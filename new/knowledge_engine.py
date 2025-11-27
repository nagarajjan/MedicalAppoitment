from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import KnowledgeEntry

class MedicalKnowledgeSystem:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def search_similar_cases(self, query, db, limit=3):
        try:
            entries = db.query(KnowledgeEntry).all()
            # CRITICAL FIX: Return empty if no history exists (prevents crash)
            if not entries or len(entries) == 0: 
                return []

            corpus = [f"{e.symptom_text} {e.diagnosis} {e.medication_plan or ''}" for e in entries]
            
            # Fit vectorizer with at least the query and one doc
            tfidf_matrix = self.vectorizer.fit_transform(corpus + [query])
            
            # Compare query (last item) against all docs (previous items)
            cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
            
            sim_scores = sorted(list(enumerate(cosine_sim[0])), key=lambda x: x[1], reverse=True)[:limit]
            
            # Only return matches with some relevance
            results = [{"score": round(score*100, 1), "data": entries[i]} for i, score in sim_scores if score > 0.05]
            return results
        except Exception as e:
            print(f"RAG Error: {e}")
            return []