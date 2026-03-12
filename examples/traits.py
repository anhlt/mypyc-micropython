"""Trait system example demonstrating mypyc-style multiple inheritance.

Traits are interface-like classes that can be mixed into other classes.
Unlike regular classes, traits:
- Cannot be instantiated directly
- Can be inherited by multiple classes
- Enable a form of multiple inheritance

Following mypyc's approach:
- Only ONE concrete base class is allowed
- Multiple traits are allowed
- Traits must come after the concrete base in the inheritance list

Uses mypy_extensions.trait decorator for compatibility with mypyc.
"""

from mypy_extensions import trait


# Define a trait for objects that can be named
@trait
class Named:
    """Trait for objects that have a name."""

    name: str

    def get_name(self) -> str:
        return self.name


# Define a trait for objects that can be described
@trait
class Describable:
    """Trait for objects that can describe themselves."""

    def describe(self) -> str:
        return "An object"


# Concrete base class
class Entity:
    """Base class for all entities."""

    id: int

    def __init__(self, id: int) -> None:
        self.id = id

    def get_id(self) -> int:
        return self.id


# Class that inherits from Entity and implements both traits
class Person(Entity, Named, Describable):
    """A person entity with name and description."""

    age: int

    def __init__(self, id: int, name: str, age: int) -> None:
        self.id = id
        self.name = name
        self.age = age

    def describe(self) -> str:
        return f"Person {self.name}, age {self.age}"

    def greet(self) -> str:
        return f"Hello, I'm {self.name}"


# Another class implementing the same traits
class Pet(Entity, Named, Describable):
    """A pet entity with name and description."""

    species: str

    def __init__(self, id: int, name: str, species: str) -> None:
        self.id = id
        self.name = name
        self.species = species

    def describe(self) -> str:
        return f"{self.species} named {self.name}"

    def make_sound(self) -> str:
        if self.species == "dog":
            return "Woof!"
        elif self.species == "cat":
            return "Meow!"
        return "..."


# Simple trait without a concrete base
@trait
class Printable:
    """Trait for objects that can be printed."""

    def to_string(self) -> str:
        return "Printable object"


class Document(Printable):
    """A document that can be printed."""

    title: str
    body: str  # renamed from 'content' to avoid QSTR conflict

    def __init__(self, title: str, body: str) -> None:
        self.title = title
        self.body = body

    def to_string(self) -> str:
        return f"Document: {self.title}"


# Test functions
def test_person() -> str:
    p = Person(1, "Alice", 30)
    return f"ID={p.get_id()}, Name={p.get_name()}, Desc={p.describe()}"


def test_pet() -> str:
    cat = Pet(2, "Whiskers", "cat")
    return f"ID={cat.get_id()}, Name={cat.get_name()}, Sound={cat.make_sound()}"


def test_document() -> str:
    doc = Document("README", "Hello World")
    return doc.to_string()


# Function accepting trait-typed parameter
def greet_named(obj: Named) -> str:
    """Accept any object implementing Named trait."""
    return obj.get_name()


def get_name_direct(obj: Named) -> str:
    """Direct attribute access on trait-typed parameter."""
    return obj.name


def test_trait_param() -> str:
    """Test passing different types to trait-typed parameter."""
    p = Person(1, "Alice", 30)
    cat = Pet(2, "Whiskers", "cat")
    # Both Person and Pet implement Named trait
    p_name: str = greet_named(p)
    cat_name: str = greet_named(cat)
    # Direct attribute access
    p_direct: str = get_name_direct(p)
    cat_direct: str = get_name_direct(cat)
    return p_name + "," + cat_name + "," + p_direct + "," + cat_direct


# Identity comparison with trait-typed parameters
def is_same_named(a: Named, b: Named) -> bool:
    """Test identity comparison with trait-typed params."""
    return a is b


def is_not_same_named(a: Named, b: Named) -> bool:
    """Test is not comparison with trait-typed params."""
    return a is not b


def is_none_named(obj: Named) -> bool:
    """Test is None comparison with trait-typed param."""
    return obj is None


def is_not_none_named(obj: Named) -> bool:
    """Test is not None comparison with trait-typed param."""
    return obj is not None


def test_trait_identity() -> str:
    """Test is/is not with trait-typed parameters."""
    p1 = Person(1, "Alice", 30)
    p2 = Person(2, "Bob", 25)

    # Same object
    same: bool = is_same_named(p1, p1)
    # Different objects
    diff: bool = is_same_named(p1, p2)
    # is not
    not_same: bool = is_not_same_named(p1, p2)
    # is not None
    not_none: bool = is_not_none_named(p1)

    r1: str = "T" if same else "F"
    r2: str = "T" if diff else "F"
    r3: str = "T" if not_same else "F"
    r4: str = "T" if not_none else "F"

    return r1 + "," + r2 + "," + r3 + "," + r4
