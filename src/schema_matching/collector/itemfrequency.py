import numbers, operator
from .. import utilities
from .base import ItemCollector
from .columntype import ColumnTypeItemCollector
from .itemcount import ItemCountCollector
from .minitem import MinItemCollector
from .maxitem import MaxItemCollector
from .variance import ItemVarianceCollector
from ..utilities.distribution import (
	UniformBinDistributionTable, SparseDistributionTable)



class ItemFrequencyCollector(ItemCollector):

	pre_dependencies = (ItemCountCollector, MinItemCollector, MaxItemCollector, ItemVarianceCollector)


	def __init__(self, previous_collector_set):
		super().__init__(previous_collector_set)

		if issubclass(previous_collector_set[ColumnTypeItemCollector].get_result(previous_collector_set), numbers.Real):
			prereqs = list(map(previous_collector_set.get, self.pre_dependencies))
			if prereqs[-1] is None:
				del prereqs[-1]
				table_ctor = UniformBinDistributionTable.for_count
			else:
				table_ctor = UniformBinDistributionTable.for_variance
			assert all(prereqs)
			utilities.iterator.map_inplace(operator.methodcaller('get_result'), prereqs)
			prereqs.append('I')
			self.frequencies = table_ctor(*prereqs)
		else:
			self.frequencies = SparseDistributionTable(int)


	def collect(self, item, collector_set=None):
		if item is not None:
			self.frequencies.increase(item)


	def get_result(self, collector_set=None):
		return self.frequencies
