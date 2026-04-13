class LatexService:
    def normalize(self, expression):
        text = str(expression).strip()
        if not text:
            return ""
        text = text.replace("\\cdot", "*")
        text = text.replace("\\times", "*")
        text = text.replace("\\pi", "pi")
        while "\\sqrt{" in text:
            start = text.find("\\sqrt{")
            inner, end = self._extract_braced(text, start + 6)
            text = text[:start] + "sqrt(" + inner + ")" + text[end:]
        while "\\frac{" in text:
            start = text.find("\\frac{")
            numerator, mid = self._extract_braced(text, start + 6)
            denominator, end = self._extract_braced(text, mid)
            text = text[:start] + "((" + numerator + ")/(" + denominator + "))" + text[end:]
        return text

    def _extract_braced(self, text, start):
        depth = 0
        chars = []
        index = start
        while index < len(text):
            char = text[index]
            if char == "{":
                depth += 1
                if depth > 1:
                    chars.append(char)
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return "".join(chars), index + 1
                chars.append(char)
            else:
                chars.append(char)
            index += 1
        raise ValueError("unbalanced braces")

