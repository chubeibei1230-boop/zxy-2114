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

def check(name, result, condition=True, expect_no_error=True):
    global passed, failed
    ok = True
    if expect_no_error and "_error" in result:
        ok = False
    elif not expect_no_error and "_error" not in result:
        ok = False
    if ok and not condition:
        ok = False
    if ok:
        passed += 1
        detail = f" (code={result.get('_error')})" if "_error" in result else ""
        print(f"  PASS: {name}{detail}")
    else:
        failed += 1
        print(f"  FAIL: {name} => {json.dumps(result, ensure_ascii=False)[:200]}")

# ====================================================
print("=" * 50)
print("Step 1: Create users")
print("=" * 50)
admin = post("/api/users/", {"username": "v_admin", "display_name": "Admin", "role": "admin"})
executor = post("/api/users/", {"username": "v_exec", "display_name": "Exec", "role": "executor"})
supervisor = post("/api/users/", {"username": "v_sup", "display_name": "Sup", "role": "supervisor"})
check("Create admin", admin)
check("Create executor", executor)
check("Create supervisor", supervisor)
aid, eid, sid = admin["id"], executor["id"], supervisor["id"]

# ====================================================
print("\n" + "=" * 50)
print("Step 2: Create stores")
print("=" * 50)
s1 = post("/api/stores/", {"name": "VStore1", "code": "VS1"}, f"operator_id={aid}")
s2 = post("/api/stores/", {"name": "VStore2", "code": "VS2"}, f"operator_id={aid}")
check("Create store 1", s1)
check("Create store 2", s2)
s1id, s2id = s1["id"], s2["id"]

# ====================================================
print("\n" + "=" * 50)
print("Step 3: Create category trees for both stores")
print("=" * 50)
food1 = post("/api/categories/", {"name": "Food", "code": "VF1", "store_id": s1id}, f"operator_id={aid}")
drink1 = post("/api/categories/", {"name": "Drink", "code": "VD1", "store_id": s1id}, f"operator_id={aid}")
snack1 = post("/api/categories/", {"name": "Snack", "code": "VS1", "store_id": s1id, "parent_id": food1["id"]}, f"operator_id={aid}")
cookie1 = post("/api/categories/", {"name": "Cookie", "code": "VC1", "store_id": s1id, "parent_id": snack1["id"]}, f"operator_id={aid}")
food2 = post("/api/categories/", {"name": "Food2", "code": "VF2", "store_id": s2id}, f"operator_id={aid}")
elec2 = post("/api/categories/", {"name": "Elec2", "code": "VE2", "store_id": s2id}, f"operator_id={aid}")
check("Create Food (store1)", food1)
check("Create Drink (store1)", drink1)
check("Create Snack (store1)", snack1)
check("Create Cookie (store1)", cookie1)
check("Create Food2 (store2)", food2)
check("Create Elec2 (store2)", elec2)

# ====================================================
print("\n" + "=" * 50)
print("Step 4: Basic category tree operations")
print("=" * 50)
tree1 = get(f"/api/categories/tree/{s1id}")
check("Get store1 tree", tree1, len(tree1) > 0)
moved = put(f"/api/categories/{snack1['id']}/move", {"new_parent_id": drink1["id"], "operated_by": aid})
check("Move Snack under Drink", moved, moved.get("parent_id") == drink1["id"])
disabled = put(f"/api/categories/{cookie1['id']}/disable", {}, f"operator_id={aid}")
check("Disable Cookie", disabled, disabled.get("is_active") == False)
enabled = put(f"/api/categories/{cookie1['id']}/enable", {}, f"operator_id={aid}")
check("Enable Cookie", enabled, enabled.get("is_active") == True)

# ====================================================
print("\n" + "=" * 50)
print("Step 5: Shelf zones and slots (normal)")
print("=" * 50)
zone1 = post("/api/shelves/zones/", {"name": "Zone1", "code": "VZ1", "store_id": s1id}, f"operator_id={aid}")
zone2 = post("/api/shelves/zones/", {"name": "Zone2", "code": "VZ2", "store_id": s2id}, f"operator_id={aid}")
slot1 = post("/api/shelves/slots/", {"zone_id": zone1["id"], "category_id": cookie1["id"], "slot_code": "S1-01", "position": 1, "capacity": 10}, f"operator_id={aid}")
check("Create zone1 (store1)", zone1)
check("Create zone2 (store2)", zone2)
check("Create slot1 (zone1 + cookie1, same store)", slot1)

# ====================================================
print("\n" + "=" * 50)
print("Step 6: Products and mountings (normal)")
print("=" * 50)
prod1 = post("/api/displays/products/", {"name": "OreoV", "sku": "SKU-V1"}, f"operator_id={aid}")
mount1 = post("/api/displays/mountings/", {"product_id": prod1["id"], "category_id": cookie1["id"], "store_id": s1id, "quantity": 5}, f"operator_id={eid}")
check("Create product", prod1)
check("Create mounting (same store)", mount1)

# ====================================================
print("\n" + "=" * 50)
print("Step 7: Display statuses")
print("=" * 50)
ds1 = post("/api/displays/statuses/", {"slot_id": slot1["id"], "product_id": prod1["id"], "status": "occupied"}, f"operator_id={eid}")
check("Create display status", ds1)

# ====================================================
print("\n" + "=" * 50)
print("Step 8: Recursive query and stats")
print("=" * 50)
rec = get(f"/api/categories/{food1['id']}/recursive")
check("Recursive stats", rec, "total_children" in rec)
vac = get("/api/stats/vacancy-categories", f"operator_id={sid}")
check("Vacancy stats", vac, isinstance(vac, list))
hf = get("/api/stats/high-frequency-moves", f"operator_id={aid}")
check("High-freq moves", hf, isinstance(hf, list))
cov = get("/api/stats/store-coverage", f"operator_id={sid}")
check("Store coverage", cov, isinstance(cov, list) and len(cov) > 0)

# ====================================================
print("\n" + "=" * 50)
print("Step 9: Merge categories")
print("=" * 50)
temp_cat = post("/api/categories/", {"name": "TempCat", "code": "VTC", "store_id": s1id, "parent_id": food1["id"]}, f"operator_id={aid}")
merged = post("/api/categories/merge", {"source_id": temp_cat["id"], "target_id": snack1["id"], "operated_by": aid})
check("Merge TempCat into Snack", merged, merged.get("name") == "Snack")

# ====================================================
print("\n" + "=" * 50)
print("Step 10: Copy category to another store (normal)")
print("=" * 50)
cp = post("/api/categories/copy", {"source_category_id": food1["id"], "target_store_id": s2id, "operated_by": aid})
check("Copy food1 to store2", cp)
tree2 = get(f"/api/categories/tree/{s2id}")
check("Store2 has more categories after copy", tree2, len(tree2) >= 2)

# ====================================================
# BUG FIX REGRESSION TESTS
# ====================================================
print("\n" + "=" * 50)
print("BUG FIX 1: Cross-store copy with wrong parent returns 400 not 500")
print("=" * 50)
bad_copy = post("/api/categories/copy", {
    "source_category_id": food1["id"],
    "target_store_id": s2id,
    "target_parent_id": food1["id"],
    "operated_by": aid
})
check("Copy with parent from wrong store => 400", bad_copy,
      bad_copy.get("_error") == 400 and "不属于目标门店" in bad_copy.get("_detail", ""),
      expect_no_error=False)

bad_copy2 = post("/api/categories/copy", {
    "source_category_id": food1["id"],
    "target_store_id": s2id,
    "target_parent_id": 99999,
    "operated_by": aid
})
check("Copy with non-existent parent => 404", bad_copy2,
      bad_copy2.get("_error") == 404 and "目标父类目不存在" in bad_copy2.get("_detail", ""),
      expect_no_error=False)

# ====================================================
print("\n" + "=" * 50)
print("BUG FIX 2: Shelf slot cannot bind category from another store")
print("=" * 50)
bad_slot_create = post("/api/shelves/slots/", {
    "zone_id": zone1["id"],
    "category_id": elec2["id"],
    "slot_code": "S1-BAD",
    "position": 2,
    "capacity": 10
}, f"operator_id={aid}")
check("Slot create: zone1(store1) + elec2(store2) => 400", bad_slot_create,
      bad_slot_create.get("_error") == 400 and "不属于同一门店" in bad_slot_create.get("_detail", ""),
      expect_no_error=False)

slot2 = post("/api/shelves/slots/", {
    "zone_id": zone1["id"],
    "category_id": drink1["id"],
    "slot_code": "S1-02",
    "position": 2,
    "capacity": 10
}, f"operator_id={aid}")
check("Slot create: zone1(store1) + drink1(store1) => OK", slot2)

bad_slot_update = put(f"/api/shelves/slots/{slot2['id']}", {
    "category_id": elec2["id"]
}, f"operator_id={aid}")
check("Slot update: bind elec2(store2) to zone1(store1) => 400", bad_slot_update,
      bad_slot_update.get("_error") == 400 and "不属于同一门店" in bad_slot_update.get("_detail", ""),
      expect_no_error=False)

# ====================================================
print("\n" + "=" * 50)
print("BUG FIX 3: Product mounting rejects cross-store category+store")
print("=" * 50)
bad_mount = post("/api/displays/mountings/", {
    "product_id": prod1["id"],
    "category_id": elec2["id"],
    "store_id": s1id,
    "quantity": 1
}, f"operator_id={eid}")
check("Mounting: elec2(store2) + store1 => 400", bad_mount,
      bad_mount.get("_error") == 400 and "跨门店挂载" in bad_mount.get("_detail", ""),
      expect_no_error=False)

good_mount = post("/api/displays/mountings/", {
    "product_id": prod1["id"],
    "category_id": drink1["id"],
    "store_id": s1id,
    "quantity": 1
}, f"operator_id={eid}")
check("Mounting: drink1(store1) + store1 => OK", good_mount)

# ====================================================
print("\n" + "=" * 50)
print("BUG FIX 4: Executor cannot update shelf slot config (admin only)")
print("=" * 50)
bad_slot_by_exec = put(f"/api/shelves/slots/{slot2['id']}", {
    "capacity": 20
}, f"operator_id={eid}")
check("Executor update slot => 403", bad_slot_by_exec,
      bad_slot_by_exec.get("_error") == 403,
      expect_no_error=False)

good_slot_by_admin = put(f"/api/shelves/slots/{slot2['id']}", {
    "capacity": 20
}, f"operator_id={aid}")
check("Admin update slot => OK", good_slot_by_admin, good_slot_by_admin.get("capacity") == 20)

# ====================================================
print("\n" + "=" * 50)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 50)
