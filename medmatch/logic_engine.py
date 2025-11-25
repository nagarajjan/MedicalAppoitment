from database import Symptom

class SymptomRouter:
    def predict_specialty(self, user_input, db_session):
        user_input = user_input.lower()
        all_symptoms = db_session.query(Symptom).all()
        scores = {}
        
        for sym in all_symptoms:
            # Case insensitive partial match
            if sym.keyword.lower() in user_input:
                if sym.specialty_id not in scores: scores[sym.specialty_id] = 0
                scores[sym.specialty_id] += 1
        
        if not scores: return None
        return max(scores, key=scores.get)