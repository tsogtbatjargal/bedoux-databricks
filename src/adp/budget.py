"""Hard spend cap for opt-in model runs (scripts/adp_eval.py --provider claude).

Before each call the provider reserves the call's worst case: a generous input
estimate plus the full max_tokens of output. A call that could cross the cap is
never sent. After the call the actual usage is charged. So the recorded spend
can't exceed the cap, whatever the model does.

Prices are USD per million tokens, from Anthropic's published list for
claude-opus-5-5 (input $4, output $20), checked 2026-11-13. Thinking tokens are
billed as output. The eval pins the model (no server-side fallback), so a reply
from any other model is an error rather than an unpriced charge.
"""

PRICES_PER_MTOK = {"claude-opus-5-5": (4.0, 20.0)}


class BudgetExceeded(RuntimeError):
    pass


def _price(model):
    for name, price in PRICES_PER_MTOK.items():
        if model == name or model.startswith(name + "-"):
            return price
    raise ValueError(f"no price for model {model!r}; refusing to charge an unknown rate")


class Budget:
    def __init__(self, cap_usd):
        if cap_usd <= 0:
            raise ValueError("cap_usd must be positive")
        self.cap_usd = float(cap_usd)
        self.spent_usd = 0.0
        self.calls = 0

    @staticmethod
    def worst_case(model, prompt_chars, max_tokens):
        # JSON averages well over 2 characters per token; chars/2 overestimates input.
        p_in, p_out = _price(model)
        return (prompt_chars / 2 + 1000) * p_in / 1e6 + max_tokens * p_out / 1e6

    def reserve(self, model, prompt_chars, max_tokens):
        worst = self.worst_case(model, prompt_chars, max_tokens)
        if self.spent_usd + worst > self.cap_usd:
            raise BudgetExceeded(
                f"next call could cost up to ${worst:.4f}; spent ${self.spent_usd:.4f} of ${self.cap_usd:.2f}")
        return worst

    def charge(self, model, input_tokens, output_tokens):
        p_in, p_out = _price(model)
        cost = input_tokens * p_in / 1e6 + output_tokens * p_out / 1e6
        self.spent_usd += cost
        self.calls += 1
        return cost
