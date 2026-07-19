import importlib.util
import unittest
from pathlib import Path

module_path = Path(__file__).resolve().parent / "test_agent3.py"
spec = importlib.util.spec_from_file_location("stock_agent_module", module_path)
stock_agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stock_agent)


class StockAgentTests(unittest.TestCase):
    def test_format_stock_results(self):
        sample = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "price": 200.0,
                "change_percent": 1.25,
                "currency": "USD",
            }
        ]

        summary = stock_agent.format_stock_results(sample)

        self.assertIn("AAPL", summary)
        self.assertIn("Apple Inc.", summary)
        self.assertIn("200.0", summary)
        self.assertIn("1.25%", summary)


if __name__ == "__main__":
    unittest.main()
