from __future__ import absolute_import, division
import collections, math, inspect
from .base import ItemCollector
from .weight import WeightDict
import utilities
import utilities.operator as uoperator
from itertools import imap, ifilter, ifilterfalse
from utilities.iterator import each
from utilities.functional import memberfn, composefn
from utilities.string import join



class ItemCollectorSet(ItemCollector, collections.OrderedDict):
  """Manages a set of collectors for a single column"""

  def __init__(self, collectors = (), predecessor = None):
    ItemCollector.__init__(self)
    collections.OrderedDict.__init__(self)

    self.predecessor = predecessor
    if predecessor:
      assert all(imap(memberfn(getattr, 'has_collected'), predecessor.itervalues()))
      self.update(predecessor)
    each(self.add, collectors)


  def collect(self, item, collector_set = None):
    assert collector_set is self
    collect = ItemCollector.collect
    collect(self, item, self)
    each(memberfn('collect', item, self),
      ifilterfalse(memberfn(getattr, 'has_collected'),
        self.itervalues()))


  class __result_type(object):

    def __init__(self, collector_set):
      object.__init__(self)
      self.__collector_set = collector_set

    def __iter__(self):
      collector_set = self.__collector_set
      return (c.get_result(collector_set) for c in collector_set.itervalues())

    def __cmp__(self, other, weights = WeightDict()):
      assert isinstance(other, type(self))
      a = self.__collector_set
      b = other.__collector_set
      if not utilities.issubset(a.iterkeys(), b):
        return weights[ItemCollectorSet].for_infinity

      def distance_of_unweighted(a_coll):
        assert a[type(a_coll)] is a_coll and type(b[type(a_coll)]) is type(a_coll)
        return a_coll.result_norm(
          a_coll.get_result(a), b[type(a_coll)].get_result(b))

      weight_sum = utilities.NonLocal(0)
      if weights is None:
        def distance_of(a_coll):
          weight_sum.value += 1
          return distance_of_unweighted(a_coll)
      else:
        def distance_of(a_coll):
          weight = weights[type(a_coll)]
          weight_sum.value += weight.for_infinity
          return weight(distance_of_unweighted(a_coll))

      value_sum = weights.sum((
        distance_of(coll) for coll in a.itervalues() if not coll.isdependency))
      if value_sum:
        assert weight_sum.value > 0
        assert not 'normalized' in weights.tags or math.fabs(value_sum / weight_sum.value) <= 1.0
        return value_sum / weight_sum.value
      else:
        return utilities.NaN


  def set_collected(self): self.__forward_call()

  def set_transformed(self): self.__forward_call()


  def __forward_call(self, fn_name=None, *args):
    if fn_name is None:
      fn_name = inspect.stack()[1][3]
    each(memberfn(fn_name, *args), self.itervalues())
    getattr(super(ItemCollectorSet, self), fn_name)(*args)


  def get_result(self, collector_set = None):
    assert collector_set is None
    return ItemCollectorSet.__result_type(self)


  result_norm = __result_type.__cmp__


  def get_transformer(self):
    transformer = composefn(*ifilter(None,
      imap(memberfn('get_transformer'),
        ifilterfalse(memberfn(getattr, 'has_transformed'),
          self.itervalues()))))
    return None if transformer is uoperator.identity else transformer


  def as_str(self, collector_set=None, format_spec=''):
    assert collector_set is None
    return join('{', u', '.join((
        join(type(collector).__name__, ': ', collector.as_str(self, format_spec))
        for collector in self.itervalues() if not collector.isdependency)),
      '}')


  def __format__(self, format_spec=''): return self.as_str(None, format_spec)


  def __str__(self): return self.as_str()


  def add(self, template, isdependency=False):
    """Adds an item collector and all its result_dependencies to this set with its type a key,
    if one of the same type isn't in the set already.

    Returns the collector the same type from this set, possibly the one just added.
    """
    collector_type = template.get_type(self.predecessor)
    collector = self.get(collector_type)

    if collector is None:
      collector = ItemCollector.get_instance(template, self.predecessor)
      if not isinstance(collector, ItemCollector):
        assert collector is None
        return None
      collector.isdependency = isdependency
      each(self.__add_dependency, collector.result_dependencies)
      collector = self.setdefault(collector_type, collector)

    collector.isdependency &= isdependency
    return collector


  def __add_dependency(self, collector):
    return self.add(collector, True)
