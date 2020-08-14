import abc
import os

import attr

from . import _reference_map
from ._compat import importlib_resources
from ._kernel import Kernel
from .python import _ClassPropertyMeta


# Yea, a global here is kind of gross, however, there's not really a better way of
# handling this. Fundamentally this is a global value, since we can only reasonably
# have a single kernel active at any one time in a real program.
kernel = Kernel()


@attr.s(auto_attribs=True, frozen=True, slots=True)
class JSIIAssembly:

    name: str
    version: str
    module: str
    filename: str

    @classmethod
    def load(cls, *args, _kernel=kernel, **kwargs):
        # Our object here really just acts as a record for our JSIIAssembly, it doesn't
        # offer any functionality itself, besides this class method that will trigger
        # the loading of the given assembly in the JSII Kernel.
        assembly = cls(*args, **kwargs)

        # Actually load the assembly into the kernel, we're using the
        # importlib.resources API here isntead of manually constructing the path, in
        # the hopes that this will make JSII modules able to be used with zipimport
        # instead of only on the FS.
        with importlib_resources.path(
            f"{assembly.module}._jsii", assembly.filename
        ) as assembly_path:
            _kernel.load(assembly.name, assembly.version, os.fspath(assembly_path))

        # Give our record of the assembly back to the caller.
        return assembly


class JSIIMeta(_ClassPropertyMeta, type):
    def __new__(cls, name, bases, attrs, *, jsii_type=None):
        # We want to ensure that subclasses of a JSII class do not require setting the
        # jsii_type keyword argument. They should be able to subclass it as normal.
        # Since their parent class will have the __jsii_type__ variable defined, they
        # will as well anyways.
        if jsii_type is not None:
            attrs["__jsii_type__"] = jsii_type

        obj = super().__new__(cls, name, bases, attrs)

        # Now that we've created the class, we'll need to register it with our reference
        # mapper. We only do this for types that are actually jsii types, and not any
        # subclasses of them.
        if jsii_type is not None:
            _reference_map.register_type(obj)

        return obj

    def __call__(cls, *args, **kwargs):
        inst = super().__call__(*args, **kwargs)

        # Register this instance with our reference map.
        _reference_map.register_reference(inst)

        return inst


class JSIIAbstractClass(abc.ABCMeta, JSIIMeta):
    pass


def enum(*, jsii_type):
    def deco(cls):
        cls.__jsii_type__ = jsii_type
        _reference_map.register_enum(cls)
        return cls

    return deco


def data_type(*, jsii_type, jsii_struct_bases, name_mapping):
    def deco(cls):
        cls.__jsii_type__ = jsii_type
        cls.__jsii_struct_bases__ = jsii_struct_bases
        cls.__jsii_name_mapping__ = name_mapping
        _reference_map.register_data_type(cls)
        return cls

    return deco


def member(*, jsii_name):
    def deco(fn):
        fn.__jsii_name__ = jsii_name
        return fn

    return deco


def implements(*interfaces):
    def deco(cls):
        cls.__jsii_type__ = getattr(cls, "__jsii_type__", None)
        cls.__jsii_ifaces__ = getattr(cls, "__jsii_ifaces__", []) + list(interfaces)
        return cls

    return deco


def interface(*, jsii_type):
    def deco(iface):
        iface.__jsii_type__ = jsii_type
        _reference_map.register_interface(iface)
        return iface

    return deco


def proxy_for(abstract_class):
    if not hasattr(abstract_class, "__jsii_proxy_class__"):
        raise TypeError(f"{abstract_class} is not a JSII Abstract class.")

    return abstract_class.__jsii_proxy_class__()


def python_jsii_mapping(cls):
    return getattr(cls, "__jsii_name_mapping__", None)
