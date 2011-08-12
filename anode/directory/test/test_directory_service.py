from anode.directory.directory_service import Directory_Service

import unittest

class Test_Directory_Service(unittest.TestCase):

    def doTest(self,directory_service):
        root = directory_service.read("/")
        print "Directory root content: " + str(root)

        # Add empty Services subtree
        directory_service.add("/","Services",{})

        root = directory_service.read("/")
        print "Directory root content: " + str(root)

        # Add a Service instance
        directory_service.add("/Services", "serv_foo.inst1", {"bar":"awesome"})

        root = directory_service.read("/")
        print "Directory root content: " + str(root)

        # Update a Service instance
        directory_service.update("/Services", "serv_foo.inst1", {"bar":"totally awesome"})

        root = directory_service.read("/")
        print "Directory root content: " + str(root)

        # Delete a Service instance
        directory_service.remove("/Services", "serv_foo.inst1")

        root = directory_service.read("/")
        print "Directory root content: " + str(root)

    def test_non_persistent(self):
        self.doTest(Directory_Service(dataStoreName='my_ds',persistent=False))

    def test_persistent(self):
        self.doTest(Directory_Service(dataStoreName='my_ds',persistent=True))

if __name__ == "__main__":
    unittest.main()
    
