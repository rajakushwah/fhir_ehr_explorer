from app.config import MAX_SEARCH_RESULTS
from app.db.neo4j import get_session


def search_concepts(search_text: str):
    if not search_text or not search_text.strip():
        return []

    q = search_text.strip()

    with get_session() as session:
        try:
            res = session.run(
                """
                CALL db.index.fulltext.queryNodes('conceptSearch', $q)
                YIELD node, score
                RETURN node.system AS conceptSystem, node.code AS conceptCode,
                       coalesce(node.display, node.text, node.code) AS label, score
                ORDER BY score DESC
                LIMIT $limit
                """,
                q=q,
                limit=MAX_SEARCH_RESULTS,
                _log_op="search/fulltext",
            )
            rows = [r.data() for r in res]
            if rows:
                return rows
        except Exception:
            pass

        res = session.run(
            """
            MATCH (c:Concept)
            WHERE toLower(coalesce(c.display, c.text, c.code)) CONTAINS toLower($q)
            RETURN c.system AS conceptSystem, c.code AS conceptCode,
                   coalesce(c.display, c.text, c.code) AS label
            LIMIT $limit
            """,
            q=q,
            limit=MAX_SEARCH_RESULTS,
            _log_op="search/fallback",
        )
        return [r.data() for r in res]
