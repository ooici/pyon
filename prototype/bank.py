"""
"""

from zope.interface import Interface, implements

from anode.service import service
from anode.net import entity
from anode.container import cc
from anode.core.bootstrap import AnodeObject
from anode.datastore.datastore import NotFoundError
from interface.services.ibank_service import IBankService

from anode.net import messaging

class BankService(service.BaseService):
    implements(IBankService)

    def new_account(self, name='', accountType='Checking'):
        res = []
        try:
            res = self.dataStore.find("BankCustomer", "Name", name)
        except NotFoundError:
            print "Customer already exists.  Customer id: " + str(res)
        if len(res) == 0:
            # Create customer info entry
            customerInfo = {}
            customerInfo["Name"] = name
            customerObj = AnodeObject("BankCustomer", customerInfo)
            customerCreateTuple = self.dataStore.create(customerObj)
            customerId = customerCreateTuple[0]

            # Create account entry
            accountInfo = {}
            accountInfo["AccountType"] = accountType
            accountInfo["Owner"] = customerId
            accountObj = AnodeObject("BankAccount", accountInfo)
            accountCreateTuple = self.dataStore.create(accountObj)
            accountId = accountCreateTuple[0]

            print "Created %s account for user %s.  Account id is %s" % (accountType, name, accountId)

        return accountId

    def deposit(self, accountId=-1, amount=0.0):
        accountObj = self.dataStore.read(accountId)
        if accountObj == None:
            return "Account does not exist"
        accountObj.Balance += amount
        self.dataStore.update(accountObj)
        return "Balance after deposit: %s" % (str(accountObj.Balance))

    def withdraw(self, accountId=-1, amount=0.0):
        accountObj = self.dataStore.read(accountId)
        if accountObj == None:
            return "Account does not exist"
        accountObj.Balance -= amount
        self.dataStore.update(accountObj)
        return "Balance after withdrawl: %s" % (str(accountObj.Balance))

    def get_balance(self, accountId=-1):
        accountObj = self.dataStore.read(accountId)
        if accountObj == None:
            return "Account does not exist"
        return "Balance: %s" % (str(accountObj.Balance))

    def list_accounts(self, name=''):
        """
        Find all accounts (optionally of type) owned by user
        """
        customerList = self.dataStore.find("BankCustomer", "Name", name)
        customerObj = customerList[0]
        return self.dataStore.find("BankAccount", "Owner", customerObj._id)

def test_service():
    bank = BankService()
    acctNum = bank.new_account('kurt', 'Savings')
    bank.balance(acctNum)
    bank.deposit(acctNum, 99999999)
    bank.balance(acctNum)
    bank.withdraw(acctNum, 1000)
    bank.list_accounts('kurt')

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

    client.new_account('kurt')
    client.deposit('kurt', 99999999)
    client.withdraw('kurt', 1000)

    #container.serve_forever()
    return client, container

if __name__ == '__main__':
    import sys
    assert len(sys.argv) > 1, 'please specify server or client'

    if sys.argv[1] == 'client':
        test_client()
    else:
        test_server()

