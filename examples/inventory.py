class Inventory:
    items: list
    counts: dict
    total_count: int

    def __init__(self) -> None:
        self.items = []
        self.counts = {}
        self.total_count = 0

    def add_item(self, item_id: int, quantity: int) -> None:
        self.items.append(item_id)
        self.counts[item_id] = quantity
        self.total_count += quantity

    def get_quantity(self, item_id: int) -> int:
        return self.counts[item_id]

    def item_count(self) -> int:
        return len(self.items)

    def total_quantity(self) -> int:
        total: int = 0
        n: int = len(self.items)
        for i in range(n):
            total += self.counts[self.items[i]]
        return total

    def has_item(self, item_id: int) -> bool:
        n: int = len(self.items)
        for i in range(n):
            val: int = self.items[i]
            if val == item_id:
                return True
        return False
