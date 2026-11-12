"""OPT-IN one Gemini call using only the fixed synthetic metadata below.
Never run as part of tests. Does not access application data or runtime quota.
"""
import argparse
import asyncio
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.ai_dispatch import Limits,AIError
from app.services.gemini_adapter import GeminiAdapter,configuration
from app.services.ai_suggestions import parse_suggestions

PAYLOAD={'schema_version':1,'columns':[{'name':'synthetic_code',
    'description':'Synthetic identifier; business owner must confirm whether required or unique.',
    'inferred_type':'text'}]}

async def main():
    parser=argparse.ArgumentParser(description='One potentially billable Gemini call; fixed synthetic metadata only.')
    parser.add_argument('--allow-provider-call',action='store_true')
    args=parser.parse_args()
    if not args.allow_provider_call:
        parser.error('Explicit --allow-provider-call is required. No call made.')
    try:
        config=configuration()
        raw=await GeminiAdapter(config).suggest(PAYLOAD,Limits())
        result=parse_suggestions(raw,['synthetic_code'])
        print(f'PASS: provider=gemini model={config.model} suggestions={len(result)}; no rules saved.')
        return 0
    except AIError as exc:
        print(f'FAIL: {exc.code}; no payload, response or credentials printed.')
        return 1
    except Exception:
        print('FAIL: smoke test error; no sensitive details printed.')
        return 1

if __name__=='__main__':sys.exit(asyncio.run(main()))
