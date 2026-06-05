import urllib.request
import json

BASE = "http://localhost:8014"

def post(path, data, params=""):
    url = f"{BASE}{path}?{params}" if params else f"{BASE}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"_error": e.code, "_detail": body}

def get(path, params=""):
    url = f"{BASE}{path}?{params}" if params else f"{BASE}{path}"
    try:
        r = urllib.request.urlopen(url)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_detail": e.read().decode()}

def put(path, data, params=""):
    url = f"{BASE}{path}?{params}" if params else f"{BASE}{path}"
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    try:
        r = urllib.request.urlopen(req)
        return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_detail": e.read().decode()}

passed = 0
failed = 0

def check(name, result, expect_no_error=True):
    global passed, failed
    if expect_no_error and "_error" not in result:
        passed += 1
        print(f"  PASS: {name}")
    elif not expect_no_error and "_error" in result:
        passed += 1
        print(f"  PASS: {name} (correctly rejected: {result.get('_error')})")
    else:
        failed += 1
        print(f"  FAIL: {name} => {result}")

print("=" * 50)
print("Step 1: Create users")
print("=" * 50)
admin = post("/api/users/", {"username": "t_admin", "display_name": "Admin", "role": "admin"})
executor = post("/api/users/", {"username": "t_exec", "display_name": "Exec", "role": "executor"})
supervisor = post("/api/users/", {"username": "t_sup", "display_name": "Sup", "role": "supervisor"})
check("Create admin", admin)
check("Create executor", executor)
check("Create supervisor", supervisor)
aid, eid, sid = admin["id"], executor["id"], supervisor["id"]

print("\n" + "=" * 50)
print("Step 2: Create stores")
print("=" * 50)
s1 = post("/api/stores/", {"name": "TestStoreA", "code": "TSA"}, f"operator_id={aid}")
s2 = post("/api/stores/", {"name": "TestStoreB", "code": "TSB"}, f"operator_id={aid}")
check("Create store A", s1)
check("Create store B", s2)
s1id, s2id = s1["id"], s2["id"]

print("\n" + "=" * 50)
print("Step 3: Create category tree")
print("=" * 50)
food = post("/api/categories/", {"name": "Food", "code": "F3", "store_id": s1id}, f"operator_id={aid}")
drink = post("/api/categories/", {"name": "Drink", "code": "D3", "store_id": s1id}, f"operator_id={aid}")
snack = post("/api/categories/", {"name": "Snack", "code": "S3", "store_id": s1id, "parent_id": food["id"]}, f"operator_id={aid}")
staple = post("/api/categories/", {"name": "Staple", "code": "ST3", "store_id": s1id, "parent_id": food["id"]}, f"operator_id={aid}")
cookie = post("/api/categories/", {"name": "Cookie", "code": "C3", "store_id": s1id, "parent_id": snack["id"]}, f"operator_id={aid}")
check("Create Food category", food)
check("Create Drink category", drink)
check("Create Snack (child of Food)", snack)
check("Create Staple (child of Food)", staple)
check("Create Cookie (child of Snack)", cookie)

print("\n" + "=" * 50)
print("Step 4: Get category tree")
print("=" * 50)
tree = get(f"/api/categories/tree/{s1id}")
check("Get category tree", tree, len(tree) > 0)

print("\n" + "=" * 50)
print("Step 5: Move category")
print("=" * 50)
moved = put(f"/api/categories/{snack['id']}/move", {"new_parent_id": drink["id"], "operated_by": aid})
check("Move Snack under Drink", moved, moved.get("parent_id") == drink["id"])
cookie_after = get(f"/api/categories/{cookie['id']}")
check("Cookie level updated after move", cookie_after, cookie_after.get("level") == 3)

print("\n" + "=" * 50)
print("Step 6: Disable/Enable category")
print("=" * 50)
disabled = put(f"/api/categories/{staple['id']}/disable", {}, f"operator_id={aid}")
check("Disable Staple", disabled, disabled.get("is_active") == False)
enabled = put(f"/api/categories/{staple['id']}/enable", {}, f"operator_id={aid}")
check("Enable Staple", enabled, enabled.get("is_active") == True)

print("\n" + "=" * 50)
print("Step 7: Create shelf zones and slots")
print("=" * 50)
zone = post("/api/shelves/zones/", {"name": "ZoneX", "code": "ZX", "store_id": s1id, "zone_type": "normal"}, f"operator_id={aid}")
slot1 = post("/api/shelves/slots/", {"zone_id": zone["id"], "category_id": cookie["id"], "slot_code": "X-01", "position": 1, "capacity": 10}, f"operator_id={aid}")
slot2 = post("/api/shelves/slots/", {"zone_id": zone["id"], "category_id": drink["id"], "slot_code": "X-02", "position": 2, "capacity": 10}, f"operator_id={aid}")
check("Create zone", zone)
check("Create slot1", slot1)
check("Create slot2", slot2)

print("\n" + "=" * 50)
print("Step 8: Create products and mountings")
print("=" * 50)
prod1 = post("/api/displays/products/", {"name": "Oreo", "sku": "SKU-T1"}, f"operator_id={aid}")
prod2 = post("/api/displays/products/", {"name": "Cola", "sku": "SKU-T2"}, f"operator_id={aid}")
mount1 = post("/api/displays/mountings/", {"product_id": prod1["id"], "category_id": cookie["id"], "store_id": s1id, "quantity": 5}, f"operator_id={eid}")
mount2 = post("/api/displays/mountings/", {"product_id": prod2["id"], "category_id": drink["id"], "store_id": s1id, "quantity": 8}, f"operator_id={eid}")
check("Create product1", prod1)
check("Create product2", prod2)
check("Create mounting1", mount1)
check("Create mounting2", mount2)

print("\n" + "=" * 50)
print("Step 9: Create display statuses")
print("=" * 50)
ds1 = post("/api/displays/statuses/", {"slot_id": slot1["id"], "product_id": prod1["id"], "status": "occupied"}, f"operator_id={eid}")
ds2 = post("/api/displays/statuses/", {"slot_id": slot2["id"], "status": "empty"}, f"operator_id={eid}")
check("Create display status (occupied)", ds1)
check("Create display status (empty)", ds2)

print("\n" + "=" * 50)
print("Step 10: Recursive query")
print("=" * 50)
rec = get(f"/api/categories/{food['id']}/recursive")
check("Recursive stats", rec, "total_children" in rec and "total_products" in rec)

print("\n" + "=" * 50)
print("Step 11: Merge categories")
print("=" * 50)
snack2 = post("/api/categories/", {"name": "Snack2", "code": "S4", "store_id": s1id, "parent_id": food["id"]}, f"operator_id={aid}")
merged = post("/api/categories/merge", {"source_id": snack2["id"], "target_id": staple["id"], "operated_by": aid})
check("Merge Snack2 into Staple", merged, merged.get("name") == "Staple")

print("\n" + "=" * 50)
print("Step 12: Copy category to another store")
print("=" * 50)
cp = post("/api/categories/copy", {"source_category_id": food["id"], "target_store_id": s2id, "operated_by": aid})
check("Copy Food to StoreB", cp)
tree2 = get(f"/api/categories/tree/{s2id}")
check("StoreB has copied categories", tree2, len(tree2) > 0)

print("\n" + "=" * 50)
print("Step 13: Statistics - Vacancy categories")
print("=" * 50)
vac = get("/api/stats/vacancy-categories", f"operator_id={sid}")
check("Get vacancy categories", vac, isinstance(vac, list))

print("\n" + "=" * 50)
print("Step 14: Statistics - High frequency moves")
print("=" * 50)
hf = get("/api/stats/high-frequency-moves", f"operator_id={aid}")
check("Get high frequency moves", hf, isinstance(hf, list))

print("\n" + "=" * 50)
print("Step 15: Statistics - Store coverage")
print("=" * 50)
cov = get("/api/stats/store-coverage", f"operator_id={sid}")
check("Get store coverage", cov, isinstance(cov, list) and len(cov) > 0)

print("\n" + "=" * 50)
print("Step 16: Filter display statuses")
print("=" * 50)
f1 = get("/api/displays/statuses/", f"store_id={s1id}&status=empty")
check("Filter by store+status", f1, isinstance(f1, list))
f2 = get("/api/displays/statuses/", f"category_id={drink['id']}")
check("Filter by category", f2, isinstance(f2, list))

print("\n" + "=" * 50)
print("Step 17: Permission control test")
print("=" * 50)
bad = post("/api/stores/", {"name": "BadStore", "code": "BAD"}, f"operator_id={eid}")
check("Executor cannot create store", bad, expect_no_error=False)

print("\n" + "=" * 50)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 50)
