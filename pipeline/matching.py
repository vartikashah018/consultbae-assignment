from rapidfuzz.fuzz import ratio


def calculate_name_similarity(name1, name2):
    """
    Return name similarity as a percentage from 0 to 100.
    """
    if not name1 or not name2:
        return 0

    return ratio(name1, name2)


def find_person_match(record, people):
    """
    Find the strongest existing person match.

    Matching priority:
    1. Exact phone
    2. Exact email
    3. Exact name + city, only when there are no identifier conflicts
    4. Fuzzy name + same city, only when there are no identifier conflicts

    We do not merge records based on a similar name alone.
    """

    best_match = None
    best_score = 0
    best_method = None

    for person in people:

        # --------------------------------------------------
        # 1. Exact phone
        # --------------------------------------------------

        if (
            record.get("phone")
            and person.get("phone")
            and record["phone"] == person["phone"]
        ):
            return person, 100, "exact_phone"

        # --------------------------------------------------
        # 2. Exact email
        # --------------------------------------------------

        if (
            record.get("email")
            and person.get("email")
            and record["email"] == person["email"]
        ):
            return person, 100, "exact_email"

        # --------------------------------------------------
        # Check for conflicting identifiers
        # --------------------------------------------------

        phone_conflict = (
            bool(record.get("phone"))
            and bool(person.get("phone"))
            and record["phone"] != person["phone"]
        )

        email_conflict = (
            bool(record.get("email"))
            and bool(person.get("email"))
            and record["email"] != person["email"]
        )

        # --------------------------------------------------
        # 3. Exact name + city
        # --------------------------------------------------

        same_name = (
            bool(record.get("name"))
            and bool(person.get("name"))
            and record["name"] == person["name"]
        )

        same_city = (
            bool(record.get("city"))
            and bool(person.get("city"))
            and record["city"] == person["city"]
        )

        if (
            same_name
            and same_city
            and not phone_conflict
            and not email_conflict
        ):
            score = 90

            if score > best_score:
                best_match = person
                best_score = score
                best_method = "exact_name_city"

        # --------------------------------------------------
        # 4. Fuzzy name + same city
        # --------------------------------------------------

        if (
            record.get("name")
            and person.get("name")
            and same_city
            and not phone_conflict
            and not email_conflict
        ):
            similarity = calculate_name_similarity(
                record["name"],
                person["name"]
            )

            if similarity >= 92:

                score = 80 + (similarity - 92) * 0.5

                if score > best_score:
                    best_match = person
                    best_score = score
                    best_method = "fuzzy_name_same_city"

    return best_match, best_score, best_method