"""
"""

from zope.interface import Interface, implements

from anode.service import service
from anode.net import entity
from anode.container import cc

from anode.net import messaging

class IBankService(Interface):

    def new_account(name):
        """
        """
        pass

    def deposit(name, amount):
        """
        """
        pass

    def withdraw(name, amount):
        """
        """
        pass

    def get_balance(name):
        """
        """
        pass

class BankService(service.BaseService):

    implements(IBankService)

    def __init__(self):
        self.accounts = {}

    def new_account(self, name):
        if name in self.accounts:
            return "Already an account"
        self.accounts[name] = 0
        return "Welcome %s" % name

    def deposit(self, name, amount):
        if name not in self.accounts:
            return "Account does not exist"
        self.accounts[name] += amount
        return "Balance: %s" % (str(self.accounts[name]),)

    def withdraw(self, name, amount):
        if name not in self.accounts:
            return "Account does not exist"
        self.accounts[name] -= amount
        return "Balance: %s" % (str(self.accounts[name]),)

    def get_balance(self, name):
        if name not in self.accounts:
            return "Account does not exist"
        return "Balance: %s" % (str(self.accounts[name]),)

def test_service():
    bank = BankService()
    bank.new_account('kurt')
    bank.deposit('kurt', 99999999)
    bank.withdraw('kurt', 1000)

def test_server():
    container = cc.Container()
    container.start() # :(
    print 'container started'

    bank_service = BankService()

    bank_entity = entity.RPCEntityFromService(bank_service)

    print 'start_server'
    container.start_server('ooibank', bank_entity)
    print 'server started'

    container.serve_forever()


def test_client():
    container = cc.Container()
    container.start() # :(

    client = entity.RPCClientEntityFromInterface(IBankService)

    container.start_client('ooibank', client)

    #container.serve_forever()
    return client, container

if __name__ == '__main__':
    test_server()
