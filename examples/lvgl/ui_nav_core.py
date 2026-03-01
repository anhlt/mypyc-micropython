def call0(f):
    return f()


_builders = {}


def register_builder(name, builder):
    _builders[name] = builder


def build_screen(name):
    builder = _builders[name]
    return call0(builder)
