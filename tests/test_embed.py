import unittest
from unittest.mock import patch, MagicMock

class TestEmbed(unittest.TestCase):
    @patch("embed.requests.post")
    def test_get_embeddings_returns_vectors(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_post.return_value = mock_resp

        import embed
        result = embed.get_embeddings(["hello", "world"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [0.1, 0.2, 0.3])

    @patch("embed.requests.post")
    def test_get_embedding_single(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_post.return_value = mock_resp

        import embed
        result = embed.get_embedding("hello")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("embed.requests.post")
    def test_get_embeddings_batches_large_input(self, mock_post):
        """Mistral embed API는 배치 제한이 있으므로 큰 입력은 분할해야 한다."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # 각 배치마다 호출
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1]} for _ in range(16)]
        }
        mock_post.return_value = mock_resp

        import embed
        texts = [f"text_{i}" for i in range(32)]
        result = embed.get_embeddings(texts)
        self.assertEqual(len(result), 32)
        # 2번 호출 (배치 크기 16)
        self.assertEqual(mock_post.call_count, 2)

if __name__ == "__main__":
    unittest.main()
