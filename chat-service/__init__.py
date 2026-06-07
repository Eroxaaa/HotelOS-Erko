class Employee:
    def __init__(self, name: str):
        self.name = name

    def work(self) -> str:
        return f"Employee {self.name} is working."

class Receptionist(Employee):
    def work(self) -> str:
        return f"Receptionist {self.name} is handling guest check-in."

class Cleaner(Employee):
    def work(self) -> str:
        # Уникальное поведение для уборщика
        return f"Cleaner {self.name} is preparing hotel rooms."


employees = [
    Receptionist("Alice"), 
    Cleaner("Bob")
]

for employee in employees:
    print(employee.work())
