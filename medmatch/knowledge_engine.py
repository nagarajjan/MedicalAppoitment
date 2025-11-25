from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from database import KnowledgeEntry

class MedicalKnowledgeSystem:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')

    def search_similar_cases(self, query, db, limit=3):
        entries = db.query(KnowledgeEntry).all()
        if not entries: return []

        corpus = [f"{e.symptom_text} {e.diagnosis}" for e in entries]
        try:
            tfidf_matrix = self.vectorizer.fit_transform(corpus + [query])
            cosine_sim = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
            sim_scores = sorted(list(enumerate(cosine_sim[0])), key=lambda x: x[1], reverse=True)[:limit]
            return [{"score": round(score*100, 1), "data": entries[i]} for i, score in sim_scores if score > 0.05]
        except:
            return []