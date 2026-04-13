class SearchService:
    DUCKDUCKGO_URL = (
        "https://api.duckduckgo.com/?q={query}&format=json&no_redirect=1"
        "&no_html=1&skip_disambig=1"
    )
    WIKIPEDIA_URL = (
        "https://en.wikipedia.org/w/api.php?action=opensearch&search={query}"
        "&limit=4&namespace=0&format=json"
    )

    def __init__(self, network):
        self.network = network

    def _urlencode(self, value):
        encoded = []
        for byte in str(value).encode("utf-8"):
            if (
                48 <= byte <= 57
                or 65 <= byte <= 90
                or 97 <= byte <= 122
                or byte in b"-_.~"
            ):
                encoded.append(chr(byte))
            elif byte == 32:
                encoded.append("+")
            else:
                encoded.append("%%%02X" % byte)
        return "".join(encoded)

    def _flatten_topics(self, items, results):
        for item in items:
            if not isinstance(item, dict):
                continue
            text_value = item.get("Text")
            if text_value:
                results.append(text_value)
            topics = item.get("Topics")
            if isinstance(topics, list):
                self._flatten_topics(topics, results)

    def search(self, query):
        if not query:
            return ["Enter a search query."]
        status = self.network.status()
        if not status.get("connected"):
            return ["WiFi is not connected.", "Open Settings first."]

        duck_url = self.DUCKDUCKGO_URL.format(query=self._urlencode(query))
        try:
            duck_data = self.network.http_get_json(duck_url)
            lines = ["Query: %s" % query, "Source: DuckDuckGo", ""]
            heading = duck_data.get("Heading")
            abstract = duck_data.get("AbstractText")
            if heading:
                lines.append("Top: %s" % heading)
            if abstract:
                lines.append(abstract)
            related = []
            self._flatten_topics(duck_data.get("RelatedTopics", []), related)
            for index, item in enumerate(related[:4], 1):
                lines.append("%s. %s" % (index, item))
            if len(lines) > 3:
                return lines
        except Exception:
            pass

        wiki_url = self.WIKIPEDIA_URL.format(query=self._urlencode(query))
        try:
            wiki_data = self.network.http_get_json(wiki_url)
            titles = wiki_data[1]
            descriptions = wiki_data[2]
            lines = ["Query: %s" % query, "Source: Wikipedia", ""]
            for index, title in enumerate(titles[:4], 1):
                lines.append("%s. %s" % (index, title))
                if index - 1 < len(descriptions) and descriptions[index - 1]:
                    lines.append(descriptions[index - 1])
            return lines
        except Exception as exc:
            return ["Search failed.", str(exc)]
