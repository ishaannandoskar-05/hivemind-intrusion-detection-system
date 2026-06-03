import time


class AttackIntelligenceAgent:

    def __init__(self):

        self.attack_history = {}
        self.blacklist = {}

        self.attack_threshold = 5
        self.blacklist_time = 120

    def update_activity(self, src_ip, attack_type):

        current_time = time.time()

        if src_ip not in self.attack_history:

            self.attack_history[src_ip] = {
                "count": 0,
                "last_attack": current_time,
                "types": set()
            }

        record = self.attack_history[src_ip]

        if attack_type != "Normal":
            record["count"] += 1
            record["last_attack"] = current_time
            record["types"].add(attack_type)

        return record

    def evaluate_threat(self, src_ip):

        if src_ip not in self.attack_history:
            return "LOW"

        record = self.attack_history[src_ip]
        attacks = record["count"]

        if attacks >= 5:
            return "CRITICAL"

        if attacks >= 3:
            return "HIGH"

        if attacks >= 1:
            return "MEDIUM"

        return "LOW"

    def update_blacklist(self, src_ip):

        severity = self.evaluate_threat(src_ip)

        if severity == "CRITICAL":

            self.blacklist[src_ip] = time.time()

            return True

        return False

    def is_blacklisted(self, src_ip):

        if src_ip not in self.blacklist:
            return False

        if time.time() - self.blacklist[src_ip] > self.blacklist_time:

            del self.blacklist[src_ip]
            return False

        return True