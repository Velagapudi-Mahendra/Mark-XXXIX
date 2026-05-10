import unittest
from unittest.mock import patch, MagicMock
import json
from actions.browser_agent import BrowserAgent, browser_agent_action

class TestBrowserAgent(unittest.TestCase):
    def setUp(self):
        self.agent = BrowserAgent()

    @patch('subprocess.run')
    def test_execute_success(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true, "data": "test"}'
        mock_run.return_value = mock_result

        result = self.agent.execute(["test-cmd"])
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], "test")
        mock_run.assert_called_once_with(["agent-browser", "test-cmd", "--json"], capture_output=True, text=True, check=True)

    @patch('subprocess.run')
    def test_browse(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true}'
        mock_run.return_value = mock_result

        self.assertTrue(self.agent.browse("https://example.com"))

    @patch('subprocess.run')
    def test_snapshot(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true, "elements": [{"ref": "@e1", "role": "button"}]}'
        mock_run.return_value = mock_result

        elements = self.agent.snapshot()
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["ref"], "@e1")

    @patch('subprocess.run')
    def test_click(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true}'
        mock_run.return_value = mock_result

        self.assertTrue(self.agent.click("@e1"))

    @patch('subprocess.run')
    def test_fill(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true}'
        mock_run.return_value = mock_result

        self.assertTrue(self.agent.fill("@e2", "hello"))

    @patch('subprocess.run')
    def test_browser_agent_action_click(self, mock_run):
        mock_result = MagicMock()
        mock_result.stdout = '{"success": true}'
        mock_run.return_value = mock_result

        res = browser_agent_action({"action": "click", "ref": "@e3"})
        self.assertEqual(res, "Clicked element @e3")

if __name__ == '__main__':
    unittest.main()
