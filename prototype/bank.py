"""
"""

from pyon.container import cc
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound
from pyon.datastore.datastore import DataStore
from pyon.net.endpoint import RPCClient
from pyon.util.log import log

from interface.services.ibank_service import IBankService, BaseBankService

class BankService(BaseBankService):

    def new_account(self, name='', account_type='Checking'):
        log.debug("In new_account")
        log.debug("name: %s" % str(name))
        log.debug("account_type: %s" % str(account_type))
        res = []
        try:
            res = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankCustomer"), ("name", DataStore.EQUAL, name)])
            print "Existing customer.  Customer id: " + str(res)
        except NotFound:
            print "New customer"
        if len(res) == 0:
            # Create customer info entry
            customer_info = {}
            customer_info["name"] = name
            customer_obj = IonObject("BankCustomer", customer_info)
            customer_create_tuple = self.clients.datastore.create(customer_obj)
            customer_id = customer_create_tuple[0]

        # Create account entry
        account_info = {}
        account_info["account_type"] = account_type
        account_info["owner"] = customer_id
        account_obj = IonObject("BankAccount", account_info)
        account_create_tuple = self.clients.datastore.create(account_obj)
        account_id = account_create_tuple[0]

        print "Created %s account for user %s.  Account id is %s" % (account_type, name, account_id)

        return account_id

    def deposit(self, account_id=-1, amount=0.0):
        account_obj = self.clients.datastore.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        account_obj.balance += amount
        self.clients.datastore.update(account_obj)
        return "Balance after deposit: %s" % (str(account_obj.balance))

    def withdraw(self, account_id=-1, amount=0.0):
        account_obj = self.clients.datastore.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        account_obj.balance -= amount
        self.clients.datastore.update(account_obj)
        return "Balance after withdrawl: %s" % (str(account_obj.balance))

    def get_balance(self, account_id=-1):
        account_obj = self.clients.datastore.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        return "Balance: %s" % (str(account_obj.balance))

    def list_accounts(self, name=''):
        """
        Find all accounts (optionally of type) owned by user
        """
        try:
            customer_list = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankCustomer"), ("name", DataStore.EQUAL, name)])
        except:
            log.error("No customers found!")
            return []
        customer_obj = customer_list[0]
        accounts = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankAccount"), ("owner", DataStore.EQUAL, customer_obj._id)])
        account_list = []
        for account in accounts:
            account_info = {}
            account_info["account_type"] = account.account_type
            account_info["balance"] = account.balance
            account_list.append(account_info)
        return account_list

def test_service():
    bank = BankService()
    acct_num = bank.new_account('kurt', 'Savings')
    bank.balance(acct_num)
    bank.deposit(acct_num, 99999999)
    bank.balance(acct_num)
    bank.withdraw(acct_num, 1000)
    bank.list_accounts('kurt')

def start_server():
    """
    This method will start the container which will
    in turn start the bank server and it's dependent
    datastore service
    """
    container = cc.Container()
    container.start() # :(
    print 'container started'

    container.serve_forever()

def start_client():
    """
    This method will start the container which will
    in turn start the bank server and it's dependent
    datastore service
    """
    container = cc.Container()
    container.start(server=False) # :(
    print 'container started'

    client = RPCClient(node=container.node, name="bank", iface=IBankService)

    print "Before start client"
    container.start(False)

    print "Before new account"
    acctNum = client.new_account('kurt', 'Savings')
    print "New account number: " + str(acctNum)
    print "Starting balance %s" % str(client.get_balance(acctNum))
    client.deposit(acctNum, 99999999)
    print "Confirming balance after deposit %s" % str(client.get_balance(acctNum))
    client.withdraw(acctNum, 1000)
    print "Confirming balance after withdrawl %s" % str(client.get_balance(acctNum))
    acctList = client.list_accounts('kurt')
    for acct_obj in acctList:
        print "Account: " + str(acct_obj)

    container.stop()

def test_single_container():
    """
    This is an all inclusive test in which the
    client and server are all running within the
    same container
    """
    container = cc.Container()
    container.start() # :(

    client = RPCClient(node=container.node, name="bank", iface=IBankService)

    print "Before start client"
    container.start(False)

    print "Before new account"
    acctNum = client.new_account('kurt', 'Savings')
    print "New account number: " + str(acctNum)
    print "Starting balance %s" % str(client.get_balance(acctNum))
    client.deposit(acctNum, 99999999)
    print "Confirming balance after deposit %s" % str(client.get_balance(acctNum))
    client.withdraw(acctNum, 1000)
    print "Confirming balance after withdrawl %s" % str(client.get_balance(acctNum))
    acctList = client.list_accounts('kurt')
    for acct_obj in acctList:
        print "Account: " + str(acct_obj)

    container.stop()

if __name__ == '__main__':
    import sys
    assert len(sys.argv) > 1, 'please specify server or client'

#    if sys.argv[1] == 'client':
#        test_client()
#    else:
#        test_server()

    test_single_container()

