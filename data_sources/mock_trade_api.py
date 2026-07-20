"""
Trade API shim — routes to the real UN Comtrade client.

This file keeps the original module name (mock_trade_api) so no agent
code needs to change. The demand_signal_agent still calls:

    from data_sources.mock_trade_api import fetch_import_data

but now gets real UN Comtrade data instead of random numbers.
The "mock" in the name is historical; the implementation is real.

If COMTRADE_API_KEY is set in the environment, uses the authenticated
endpoint (500 calls/day free tier). If not set, uses the free preview
endpoint (annual data, no key required).

Either way, falls back to deterministic mock data if the API is
unreachable — so the app always works even without internet.
"""

from data_sources.comtrade_api import fetch_import_data  # noqa: F401
