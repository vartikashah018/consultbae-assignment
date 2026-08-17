from matching import find_person_match


people = [
    {
        "id": 1,
        "name": "rahul kumar",
        "email": "rahul@example.com",
        "phone": "9000000001",
        "city": "delhi",
    },
    {
        "id": 2,
        "name": "ritu sharma",
        "email": "ritu@example.com",
        "phone": "9000000002",
        "city": "noida",
    },
]


# Test 1: exact phone
record = {
    "name": "different name",
    "email": "",
    "phone": "9000000001",
    "city": "mumbai",
}

match, score, method = find_person_match(
    record,
    people
)

print("TEST 1")
print(match)
print(score)
print(method)


# Test 2: exact email
record = {
    "name": "someone",
    "email": "ritu@example.com",
    "phone": "",
    "city": "noida",
}

match, score, method = find_person_match(
    record,
    people
)

print("\nTEST 2")
print(match)
print(score)
print(method)


# Test 3: exact name + city
record = {
    "name": "ritu sharma",
    "email": "",
    "phone": "",
    "city": "noida",
}

match, score, method = find_person_match(
    record,
    people
)

print("\nTEST 3")
print(match)
print(score)
print(method)


# Test 4: same name but different city
record = {
    "name": "ritu sharma",
    "email": "",
    "phone": "",
    "city": "delhi",
}

match, score, method = find_person_match(
    record,
    people
)

print("\nTEST 4")
print(match)
print(score)
print(method)