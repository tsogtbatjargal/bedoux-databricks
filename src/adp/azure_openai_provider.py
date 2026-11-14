"""Opt-in Azure OpenAI provider for the Track 4 investigator.

Same contract and system prompt as claude_provider: complete(payload, timeout_s)
-> str, called only with a CheckedPayload's text, reply re-validated by
send_payload. It adds no authority. Added so the real-model eval can run on
Azure credits (Microsoft-billed Foundry Models meter); results are reported
separately and describe this model, not Claude.

Configuration (never committed): AZURE_OPENAI_ENDPOINT (the resource endpoint),
AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT. Requires `uv sync --group agents`.
"""

import os
import time

from src.adp.claude_provider import SYSTEM

MAX_COMPLETION_TOKENS = 16000


class AzureOpenAIProvider:
    """model: the underlying model id used for pricing (the deployment name can
    differ). budget: an adp.budget.Budget reserved before every call."""

    def __init__(self, model, deployment=None, effort="medium", client=None, budget=None):
        import openai  # deferred: the agents group is optional

        self._openai = openai
        self.model = model
        self.deployment = deployment or os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.effort = effort
        self.budget = budget
        self.client = client or openai.OpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            base_url=os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/") + "/openai/v1/",
        )
        self.usage = []

    def complete(self, payload, *, timeout_s):
        openai = self._openai
        if self.budget is not None:
            self.budget.reserve(self.model, len(SYSTEM) + len(payload), MAX_COMPLETION_TOKENS)
        started = time.monotonic()
        try:
            response = self.client.with_options(timeout=timeout_s, max_retries=1).chat.completions.create(
                model=self.deployment,
                messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": payload}],
                max_completion_tokens=MAX_COMPLETION_TOKENS,
                reasoning_effort=self.effort,
                response_format={"type": "json_object"},
            )
        except openai.APITimeoutError as exc:
            raise TimeoutError from exc
        usage = response.usage
        if not response.model.startswith(self.model):
            raise ValueError(f"deployment answered with {response.model!r}, expected {self.model!r}")
        cost = (self.budget.charge(self.model, usage.prompt_tokens, usage.completion_tokens)
                if self.budget is not None else None)
        choice = response.choices[0]
        self.usage.append({
            "seconds": round(time.monotonic() - started, 2), "cost_usd": cost,
            "model": response.model, "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens, "stop_reason": choice.finish_reason,
            "request_id": response.id,
        })
        if choice.message.refusal:
            raise RuntimeError("model refused")  # send_payload maps this to provider_error
        return (choice.message.content or "").strip()
