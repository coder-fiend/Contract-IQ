from backend.services.query_classifier import query_classifier, QueryType

def test_classification():
    # Without document
    q1 = "My landlord is refusing to return my security deposit of 50000"
    t1 = query_classifier.classify(q1, has_document=False)
    assert t1 == QueryType.REAL_WORLD_QUERY, f"Expected REAL_WORLD_QUERY, got {t1}"
    print(f"'{q1}' -> {t1} [PASS]")

    q2 = "What does Section 27 of Indian Contract Act say about non-compete?"
    t2 = query_classifier.classify(q2, has_document=False)
    assert t2 == QueryType.LEGAL_QUERY, f"Expected LEGAL_QUERY, got {t2}"
    print(f"'{q2}' -> {t2} [PASS]")

    q3 = "What is the difference between IPC 420 and BNS 318?"
    t3 = query_classifier.classify(q3, has_document=False)
    assert t3 == QueryType.LEGAL_QUERY, f"Expected LEGAL_QUERY, got {t3}"
    print(f"'{q3}' -> {t3} [PASS]")

    # With document uploaded
    q4 = "What is the notice period mentioned in clause 4?"
    t4 = query_classifier.classify(q4, has_document=True)
    assert t4 == QueryType.DOCUMENT_QUERY, f"Expected DOCUMENT_QUERY, got {t4}"
    print(f"'{q4}' -> {t4} [PASS]")

    q5 = "Does clause 8 in this agreement violate Section 27 of the Indian Contract Act?"
    t5 = query_classifier.classify(q5, has_document=True)
    assert t5 == QueryType.HYBRID_QUERY, f"Expected HYBRID_QUERY, got {t5}"
    print(f"'{q5}' -> {t5} [PASS]")

    print("ALL QUERY CLASSIFICATION TESTS PASSED!")

if __name__ == "__main__":
    test_classification()
