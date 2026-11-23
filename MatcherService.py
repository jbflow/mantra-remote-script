class MatcherService:
    def levenshtein_distance(self, a, b):
        a = a or ""
        b = b or ""
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        previous_row = list(range(len(b) + 1))
        for i, ca in enumerate(a, start=1):
            current_row = [i]
            for j, cb in enumerate(b, start=1):
                insertions = previous_row[j] + 1
                deletions = current_row[j - 1] + 1
                substitutions = previous_row[j - 1] + (ca != cb)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def normalized_distance(self, a, b):
        if not a and not b:
            return 0.0
        return float(self.levenshtein_distance(a, b)) / float(max(len(a), len(b), 1))

    def best_match(self, query, candidates, key=None, threshold=0.6):
        if not query or not candidates:
            return None
        key_fn = key if key else lambda item: item
        query_text = str(query).strip().lower()
        if not query_text:
            return None

        best_item = None
        best_score = 1.0
        query_tokens = [token for token in query_text.replace("/", " ").split() if token]

        for item in candidates:
            try:
                raw = key_fn(item)
            except Exception:
                raw = None
            candidate = str(raw or "").strip().lower()
            if not candidate:
                continue
            if query_text == candidate:
                return item
            candidate_tokens = [token for token in candidate.replace("/", " ").split() if token]
            if query_tokens and all(token in candidate_tokens for token in query_tokens):
                score = 0.0
            elif query_text in candidate:
                score = 0.1
            else:
                score = self.normalized_distance(query_text, candidate)
            if score < best_score:
                best_score = score
                best_item = item

        if best_item and best_score <= threshold:
            return best_item
        return None
