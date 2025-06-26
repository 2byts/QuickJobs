import csv
import json
import os
import logging
from datetime import datetime

class CSVDatabase:
    def __init__(self, base_path="data"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)
        self.registration_file = os.path.join(base_path, "registration_data.csv")
        self.users_file = os.path.join(base_path, "users.csv")
        self.withdrawals_file = os.path.join(base_path, "withdrawals.csv")
        self.balance_file = os.path.join(base_path, "balance.csv")  # now only main balances
        self.hold_balance_file = os.path.join(base_path, "hold_balances.csv")  # new for per FB hold balances
        self.logger = logging.getLogger(__name__)
        self._init_csv_files()

    def _init_csv_files(self):
        # Initialize registration data file
        if not os.path.exists(self.registration_file):
            with open(self.registration_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["id", "user_id", "data", "timestamp", "approved"])

        # Initialize users file
        if not os.path.exists(self.users_file):
            with open(self.users_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["user_id", "username"])

        # Initialize withdrawals file
        if not os.path.exists(self.withdrawals_file):
            with open(self.withdrawals_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["id", "user_id", "amount", "wallet", "payment_method", "status", "timestamp"])

        # Initialize balance file (only main balance now)
        if not os.path.exists(self.balance_file):
            with open(self.balance_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["user_id", "main_balance"])

        # Initialize hold balances file (new)
        if not os.path.exists(self.hold_balance_file):
            with open(self.hold_balance_file, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["user_id", "facebook_id", "hold_balance"])

    # ---------- USERS ----------
    def add_user(self, user_id, username):
        users = self.get_all_users()
        if any(str(u["user_id"]) == str(user_id) for u in users):
            return True  # Already exists
        try:
            with open(self.users_file, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([user_id, username])
            return True
        except Exception as e:
            self.logger.error(f"Failed to add user: {e}")
            return False

    def get_all_users(self):
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            self.logger.error(f"Failed to get users: {e}")
            return []

    # ---------- REGISTRATION ----------
    def _read_all_registrations(self):
        data = []
        try:
            with open(self.registration_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        row["data"] = json.loads(row["data"])
                        row["approved"] = row.get("approved", "false").lower() == "true"
                        data.append(row)
                    except json.JSONDecodeError:
                        self.logger.error(f"Invalid JSON in registration ID {row['id']}")
        except Exception as e:
            self.logger.error(f"Read registration error: {e}")
        return data

    def store_registration_data(self, user_id, data):
        all_regs = self._read_all_registrations()
        password = data.get("password")
        timestamp = datetime.utcnow().isoformat()
        updated = False

        for reg in all_regs:
            if reg["user_id"] == str(user_id) and reg["data"].get("password") == password:
                reg["data"] = data
                reg["timestamp"] = timestamp
                updated = True
                break

        try:
            with open(self.registration_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "data", "timestamp", "approved"])
                for i, row in enumerate(all_regs, start=1):
                    writer.writerow([i, row["user_id"], json.dumps(row["data"], ensure_ascii=False), row["timestamp"], row.get("approved", False)])
                if not updated:
                    new_id = len(all_regs) + 1
                    writer.writerow([new_id, user_id, json.dumps(data, ensure_ascii=False), timestamp, False])
            return True
        except Exception as e:
            self.logger.error(f"Failed to store registration: {e}")
            return False

    def get_registration_data(self, user_id):
        all_regs = self._read_all_registrations()
        user_regs = [r for r in all_regs if r["user_id"] == str(user_id)]
        if not user_regs:
            return None
        # Return the latest by timestamp
        latest_reg = max(user_regs, key=lambda x: x["timestamp"])
        return latest_reg["data"]

    def approve_registration(self, user_id, password, status: bool):
        all_regs = self._read_all_registrations()
        changed = False
        for r in all_regs:
            if r["user_id"] == str(user_id) and r["data"].get("password") == password:
                r["approved"] = status
                changed = True
                break
        if not changed:
            return False

        try:
            with open(self.registration_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "data", "timestamp", "approved"])
                for i, row in enumerate(all_regs, start=1):
                    writer.writerow([i, row["user_id"], json.dumps(row["data"], ensure_ascii=False), row["timestamp"], row["approved"]])
            return True
        except Exception as e:
            self.logger.error(f"Approval update failed: {e}")
            return False

    def clear_registration_data(self, user_id):
        all_regs = self._read_all_registrations()
        filtered = [r for r in all_regs if r["user_id"] != str(user_id)]

        try:
            with open(self.registration_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "data", "timestamp", "approved"])
                for i, row in enumerate(filtered, start=1):
                    writer.writerow([i, row["user_id"], json.dumps(row["data"], ensure_ascii=False), row["timestamp"], row.get("approved", False)])
            return True
        except Exception as e:
            self.logger.error(f"Failed to clear registration data for user {user_id}: {e}")
            return False

    def reject_registration(self, user_id, password):
        # Remove registration
        registrations = self._read_all_registrations()
        filtered = [r for r in registrations if not (r["user_id"] == str(user_id) and r["data"].get("password") == password)]

        # Identify Facebook ID from rejected registration to remove its hold balance
        fb_id_to_remove = None
        for r in registrations:
            if r["user_id"] == str(user_id) and r["data"].get("password") == password:
                fb_id_to_remove = r["data"].get("facebook_id")
                break

        try:
            with open(self.registration_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "user_id", "data", "timestamp", "approved"])
                for i, row in enumerate(filtered, start=1):
                    writer.writerow([i, row["user_id"], json.dumps(row["data"], ensure_ascii=False), row["timestamp"], row["approved"]])
        except Exception as e:
            self.logger.error(f"Failed to delete rejected registration: {e}")
            return False

        # Remove hold balance for specific facebook_id only
        if fb_id_to_remove:
            self.remove_hold_balance_for_facebook_id(user_id, fb_id_to_remove)

        return True
    
    # ----------- Account Details ---------

    def _read_all_registrations(self):
        data = []
        try:
            with open(self.registration_file, "r", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    try:
                        row["data"] = json.loads(row["data"])
                        row["approved"] = row.get("approved", "false").lower() == "true"
                        data.append(row)
                    except json.JSONDecodeError:
                        # handle or log invalid JSON
                        pass
        except Exception as e:
            # handle or log error
            pass
        return data

    def get_account_status(self, user_id: int) -> dict:
        all_data = self._read_all_registrations()
        counts = {"success": 0, "hold": 0, "rejected": 0}
    
        for row in all_data:
            if str(row.get("user_id")) != str(user_id):
                continue

        approved = row.get("approved")
        
        # Handle bool or string
        if approved is True or (isinstance(approved, str) and approved.lower() == "true"):
            counts["success"] += 1
        elif approved is False or (isinstance(approved, str) and approved.lower() == "false"):
            counts["hold"] += 1
        else:
            counts["rejected"] += 1
    
        return counts

    def get_user_accounts(self, user_id, limit=5, offset=0):
        # Return list of accounts for the user, paginated
        regs = [r for r in self._read_all_registrations() if r["user_id"] == str(user_id)]
        
        # Sort by timestamp desc (latest first)
        regs.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Slice for pagination
        paged_regs = regs[offset:offset + limit]
        
        # Map to simplified structure for the UI
        accounts = []
        for reg in paged_regs:
            status = "hold"
            if reg.get("approved") is True:
                status = "success"
            elif reg.get("approved") is False:
                status = "rejected"
            
            accounts.append({
                "id": reg["id"],
                "status": status,
                "timestamp": reg["timestamp"],
            })
        return accounts

    # ---------- WITHDRAWALS ----------
    def add_withdrawal(self, user_id, amount, wallet, payment_method="bkash", status="pending"):
        all_rows = self.get_all_withdrawals()
        new_id = max([int(r["id"]) for r in all_rows], default=0) + 1
        timestamp = datetime.utcnow().isoformat()
        try:
            with open(self.withdrawals_file, "a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([new_id, user_id, amount, wallet, payment_method, status, timestamp])
            return True
        except Exception as e:
            self.logger.error(f"Failed to store withdrawal: {e}")
            return False

    def get_all_withdrawals(self):
        try:
            with open(self.withdrawals_file, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            self.logger.error(f"Failed to read withdrawals: {e}")
            return []

    # ---------- BALANCES ----------
    def _normalize_balance(self, val):
        try:
            return float(val)
        except Exception:
            return 0.0

    def get_user_main_balance(self, user_id):
        balances = self.get_all_balances()
        for row in balances:
            if row["user_id"] == str(user_id):
                return self._normalize_balance(row.get("main_balance", 0))
        return 0.0

    def get_all_balances(self):
        try:
            with open(self.balance_file, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            self.logger.error(f"Balance read error: {e}")
            return []

    def update_user_main_balance(self, user_id, amount):
        balances = self.get_all_balances()
        updated = False
        for b in balances:
            if b["user_id"] == str(user_id):
                b["main_balance"] = str(amount)
                updated = True
                break
        if not updated:
            balances.append({
                "user_id": str(user_id),
                "main_balance": str(amount)
            })

        try:
            with open(self.balance_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["user_id", "main_balance"])
                for row in balances:
                    writer.writerow([row["user_id"], row["main_balance"]])
            return True
        except Exception as e:
            self.logger.error(f"Failed to update main balance: {e}")
            return False

    # ---------- HOLD BALANCES PER FACEBOOK ID ----------
    def _read_all_hold_balances(self):
        try:
            with open(self.hold_balance_file, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except Exception as e:
            self.logger.error(f"Failed to read hold balances: {e}")
            return []

    def _write_all_hold_balances(self, data):
        try:
            with open(self.hold_balance_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["user_id", "facebook_id", "hold_balance"])
                for row in data:
                    writer.writerow([row["user_id"], row["facebook_id"], row["hold_balance"]])
            return True
        except Exception as e:
            self.logger.error(f"Failed to write hold balances: {e}")
            return False

    def add_hold_balance_for_facebook_id(self, user_id, facebook_id, amount):
        holds = self._read_all_hold_balances()
        updated = False
        for row in holds:
            if row["user_id"] == str(user_id) and row["facebook_id"] == facebook_id:
                new_amount = self._normalize_balance(row["hold_balance"]) + amount
                row["hold_balance"] = str(new_amount)
                updated = True
                break
        if not updated:
            holds.append({"user_id": str(user_id), "facebook_id": facebook_id, "hold_balance": str(amount)})

        return self._write_all_hold_balances(holds)

    def get_hold_balance_for_facebook_id(self, user_id, facebook_id):
        holds = self._read_all_hold_balances()
        for row in holds:
            if row["user_id"] == str(user_id) and row["facebook_id"] == facebook_id:
                return self._normalize_balance(row["hold_balance"])
        return 0.0

    def move_hold_to_main_for_facebook_id(self, user_id, facebook_id):
        holds = self._read_all_hold_balances()
        amount = 0.0
        new_holds = []
        for row in holds:
            if row["user_id"] == str(user_id) and row["facebook_id"] == facebook_id:
                amount = self._normalize_balance(row["hold_balance"])
                # skip to remove this row
            else:
                new_holds.append(row)

        if amount > 0:
            # Update hold_balances.csv without this facebook_id
            if not self._write_all_hold_balances(new_holds):
                return 0.0

            # Add amount to main balance
            main_balance = self.get_user_main_balance(user_id)
            new_main = main_balance + amount
            if not self.update_user_main_balance(user_id, new_main):
                self.logger.error(f"Failed to update main balance for user {user_id} during hold transfer.")
                return 0.0
            return amount
        return 0.0

    def remove_hold_balance_for_facebook_id(self, user_id, facebook_id):
        holds = self._read_all_hold_balances()
        new_holds = [row for row in holds if not (row["user_id"] == str(user_id) and row["facebook_id"] == facebook_id)]
        return self._write_all_hold_balances(new_holds)

  # ---------- STATS ----------
    def get_total_users(self):
        return len(self.get_all_users())

    def get_total_registrations(self):
        return len(self._read_all_registrations())

    def get_all_registration_details(self):
        return [(r["user_id"], r["data"]) for r in self._read_all_registrations()]
