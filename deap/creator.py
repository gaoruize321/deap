#    This file is part of DEAP.
#
#    DEAP is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of
#    the License, or (at your option) any later version.
#
#    DEAP is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with DEAP. If not, see <http://www.gnu.org/licenses/>.

"""The :mod:`~deap.creator` module is the heart and soul of DEAP, it allows to
create, at runtime, classes that will fulfill the needs of your evolutionary
algorithms. This module follows the meta-factory paradigm by allowing to
create new classes via both composition and inheritance. Attributes both datas
and functions are added to existing types in order to create new types
empowered with user specific evolutionary computation capabilities. In effect,
new classes can be built from any imaginable type, from :class:`list` to
:class:`set`, :class:`dict`, :class:`~deap.base.Tree` and more,
providing the possibility to implement genetic algorithms, genetic
programming, evolution strategies, particle swarm optimizers, and many more.
"""

import array
import copy

class_replacers = {}
"""Some classes in Python's standard library as well as third party library
may be in part incompatible with the logic used in DEAP. In order to palliate
to this problem, the method :func:`create` uses the dictionary
`class_replacers` to identify if the base type provided is problematic, and if
so  the new class inherits from the replacement class instead of the
original base class.

`class_replacers` keys are classes to be replaced and the values are the
replacing classes.
"""

try:
    import numpy
except ImportError:
    pass
else:
    class _numpy_array(numpy.ndarray):
        def __deepcopy__(self, memo):
            """Overrides the deepcopy from numpy.ndarray that does not copy
            the object's attributes.
            """
            copy_ = numpy.ndarray.__deepcopy__(self, memo)
            copy_.__dict__.update(copy.deepcopy(self.__dict__, memo))
            return copy_

        @staticmethod
        def __new__(cls, iterable):
            """Creates a new instance of a numpy.ndarray from a function call"""
            return numpy.array(list(iterable)).view(cls)

        def __array_finalize__(self, obj):
            # __init__ will reinitialize every member of the subclass.
            # this might not be desirable for example in the case of an ES. 
            self.__init__()

            # Instead, e could use the following that will simply deepcopy 
            # every member that is present in the original class
            # This is significantly slower. 
            #if self.__class__ == obj.__class__:
            #    self.__dict__.update(copy.deepcopy(obj.__dict__))
    class_replacers[numpy.ndarray] = _numpy_array

class _array(array.array):
    @staticmethod
    def __new__(cls, seq=()):
        return super(_array, cls).__new__(cls, cls.typecode, seq)
    
    def __deepcopy__(self, memo):
        """Overrides the deepcopy from array.array that does not copy
        the object's attributes and class type.
        """
        cls = self.__class__
        copy_ = cls.__new__(cls, self)
        memo[id(self)] = copy_
        copy_.__dict__.update(copy.deepcopy(self.__dict__, memo))
        return copy_

    def __reduce__(self):
        return (self.__class__, (list(self),), self.__dict__)
class_replacers[array.array] = _array

def create(name, base, **kargs):
    """Creates a new class named *name* inheriting from *base* in the
    :mod:`~deap.creator` module. The new class can have attributes defined by
    the subsequent keyword arguments passed to the function create. If the
    argument is a class (without the parenthesis), the __init__ function is
    called in the initialization of an instance of the new object and the
    returned instance is added as an attribute of the class' instance.
    Otherwise, if the argument is not a class, (for example an :class:`int`),
    it is added as a "static" attribute of the class.
    
    The following is used to create a class :class:`Foo` inheriting from the
    standard :class:`list` and having an attribute :attr:`bar` being an empty
    dictionary and a static attribute :attr:`spam` initialized to 1. ::
    
        create("Foo", list, bar=dict, spam=1)
        
    This above line is exactly the same as defining in the :mod:`creator`
    module something like the following. ::
    
        def Foo(list):
            spam = 1
            
            def __init__(self):
                self.bar = dict()
    """
    dict_inst = {}
    dict_cls = {}
    for obj_name, obj in kargs.iteritems():
        if hasattr(obj, "__call__"):
            dict_inst[obj_name] = obj
        else:
            dict_cls[obj_name] = obj

    # Check if the base class has to be replaced
    if base in class_replacers:
        base = class_replacers[base]

    # A DeprecationWarning is raised when the object inherits from the 
    # class "object" which leave the option of passing arguments, but
    # raise a warning stating that it will eventually stop permitting
    # this option. Usually this happens when the base class does not
    # override the __init__ method from object.
    def initType(self, *args, **kargs):
        """Replace the __init__ function of the new type, in order to
        add attributes that were defined with **kargs to the instance.
        """
        for obj_name, obj in dict_inst.iteritems():
            setattr(self, obj_name, obj())
        if base.__init__ is not object.__init__:
            base.__init__(self, *args, **kargs)
        else:
            base.__init__(self)

    objtype = type(name, (base,), dict_cls)
    objtype.__init__ = initType
    globals()[name] = objtype