"""
test that all modules in pyon have valid syntax and can be imported successfully
"""

import os
from unittest import TestCase,main
import ooi.testing
import __main__
from nose.plugins.attrib import attr

MODULES=[ 'examples', 'interface', 'pyon', 'prototype', 'putil' ]

@attr('UNIT')
class TestProjectImports(ooi.testing.ImportTest):
    def __init__(self,*a,**b):
        # for utilities project only, want to search in BASE/src
        # but this test is in BASE/pyon/core/test
        # so have to go up three levels
        source_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        super(TestProjectImports,self).__init__(source_dir, MODULES, *a, **b)


if __name__ == '__main__':
    main()