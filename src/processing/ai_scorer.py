"""AI scoring using Claude API with web search — researches each org actively."""
import os
import json
import time
import anthropic
import pandas as pd

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a research analyst evaluating whether a newly registered 
501(c)(3) nonprofit is a practical outreach prospect for FACTS to contact about 
becoming or supporting a Scholarship Granting Organization (SGO), Student Tuition 
Organization (STO), Student Scholarship Organization (SSO), or similar K-12 
scholarship-granting intermediary.

For each organization:
1. Search the web for the organization by name and state
2. Look for evidence of K-12 education focus, faith-based school support, 
   tuition assistance, or scholarship granting activity
3. Check whether their state has an active SGO/STO program
4. Look for any news, website content, or public records that indicate their mission

Respond ONLY with valid JSON, no preamble, no markdown:
{
  "score": <integer 0-100>,
  "recommendation": "<two to three sentences explaining your confidence level and exactly how you arrived at the score. Mention specific things you found in your research.>"
}

Scoring guide:
90-100: Definitely - Already operates scholarships or tuition assistance for K-12, in active SGO state
80-89:  Likely - Strong K-12 education or faith-based school mission, in active SGO state
70-79:  Potentially - Clear education focus with signals pointing toward K-12, in active SGO state
50-69:  Moderate — general education or youth nonprofit, plausible SGO candidate
20-49:  Weak — tangential connection to education, unlikely but possible
0-19:   Unlikely — mission unrelated to K-12 education or scholarship granting"""


def _build_prompt(row: pd.Series) -> str:
    return (
        f"Organization Name: {row.get('NAME', '')}\n"
        f"State: {row.get('STATE', '')}\n"
        f"NTEE Code: {row.get('NTEE_CD', '')}\n"
        f"Website on file: {row.get('website', 'None found')}\n"
        f"Ruling Date: {row.get('RULING', '')}\n\n"
        f"Please research this organization and evaluate its likelihood of becoming "
        f"or supporting a K-12 Scholarship Granting Organization."
    )


def score_with_ai(df: pd.DataFrame, threshold: float = 40.0) -> pd.DataFrame:
    """
    For rows above threshold, use Claude with web search to research
    each org and produce a score + written recommendation.
    Adds 'ai_score' and 'ai_recommendation' columns.
    """
    df = df.copy()
    df['ai_score'] = pd.NA
    df['ai_recommendation'] = ''

    eligible = df[df['combined_score'] >= threshold].copy()
    print(f"  AI researching {len(eligible)} orgs (combined_score >= {threshold})")

    if eligible.empty:
        return df

    # Build batch requests with web search tool enabled
    requests = []
    for idx, row in eligible.iterrows():
        requests.append(
            anthropic.types.message_create_params.Request(
                custom_id=str(idx),
                params={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "tools": [
                        {
                            "type": "web_search_20250305",
                            "name": "web_search"
                        }
                    ],
                    "messages": [
                        {"role": "user", "content": _build_prompt(row)}
                    ],
                }
            )
        )

    # Submit batch
    batch = client.messages.batches.create(requests=requests)
    print(f"  Batch submitted: {batch.id}")

    # Poll until complete
    while True:
        batch = client.messages.batches.retrieve(batch.id)
        done = batch.request_counts.succeeded + batch.request_counts.errored
        print(f"  Status: {batch.processing_status} | {done}/{len(requests)} complete")
        if batch.processing_status == "ended":
            break
        time.sleep(15)

    # Parse results
    failed = 0
    for result in client.messages.batches.results(batch.id):
        idx = int(result.custom_id)
        if result.result.type == "succeeded":
            try:
                # Find the final text block — web search means
                # there may be multiple content blocks before the JSON
                text = None
                for block in reversed(result.result.message.content):
                    if hasattr(block, 'text'):
                        text = block.text
                        break

                if text:
                    # Strip any accidental markdown fences
                    text = text.strip().removeprefix("```json").removesuffix("```").strip()
                    parsed = json.loads(text)
                    df.at[idx, 'ai_score'] = int(parsed['score'])
                    df.at[idx, 'ai_recommendation'] = parsed.get('recommendation', '')
            except Exception as e:
                failed += 1
                print(f"  Parse error idx {idx}: {e}")
        else:
            failed += 1

    print(f"  Complete — {len(eligible) - failed} scored, {failed} failed")
    return df
