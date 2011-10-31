"""
"""
from time import sleep

from pyon.public import Container
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
            res = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankCustomer"), DataStore.AND, ("name", DataStore.EQUAL, name)])
            customer_info = res[0]
            customer_id = customer_info._id
        except NotFound:
            # New customer
            pass
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
            customer_list = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankCustomer"), DataStore.AND, ("name", DataStore.EQUAL, name)])
        except:
            log.error("No customers found!")
            return []
        customer_obj = customer_list[0]
        accounts = self.clients.datastore.find([("type_", DataStore.EQUAL, "BankAccount"), DataStore.AND, ("owner", DataStore.EQUAL, customer_obj._id)])
        return accounts
#        account_list = []
#        for account in accounts:
#            account_info = {}
#            account_info["account_type"] = account.account_type
#            account_info["balance"] = account.balance
#            account_list.append(account_info)
#        return account_list

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
    container = Container()
    container.start() # :(
    container.start_rel_from_url("res/deploy/r2deploy.yml")
    print 'container started'

    container.serve_forever()

def start_client():
    """
    This method will start the container which will
    in turn start the bank server and it's dependent
    datastore service
    """
    container = Container()
    container.start() # :(
    print 'container started'

    client = RPCClient(node=container.node, name="bank", iface=IBankService)

    print "Before new account"
    savingsAcctNum = client.new_account('kurt', 'Savings')
    print "New savings account number: " + str(savingsAcctNum)
    print "Starting savings balance %s" % str(client.get_balance(savingsAcctNum))
    client.deposit(savingsAcctNum, 99999999)
    print "Confirming savings balance after deposit %s" % str(client.get_balance(savingsAcctNum))
    client.withdraw(savingsAcctNum, 1000)
    print "Confirming savings balance after withdrawl %s" % str(client.get_balance(savingsAcctNum))

    checkingAcctNum = client.new_account('kurt', 'Checking')
    print "New checking account number: " + str(checkingAcctNum)
    print "Starting checking balance %s" % str(client.get_balance(checkingAcctNum))
    client.deposit(checkingAcctNum, 99999999)
    print "Confirming checking balance after deposit %s" % str(client.get_balance(checkingAcctNum))
    client.withdraw(checkingAcctNum, 1000)
    print "Confirming checking balance after withdrawl %s" % str(client.get_balance(checkingAcctNum))

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
    container = Container()
    container.start() # :(
    container.start_rel_from_url("res/deploy/r2deploy.yml")

    server_listen_ready_list = container.start_rel_from_url('res/deploy/r2deploy.yml')

    # wait for them to spawn: this is horribad, figure out better practice
    for x in server_listen_ready_list:
        print "Waiting for server listen ready"
        x.get()
        print ".. done"

    client = RPCClient(node=container.node, name="bank", iface=IBankService)

    print "Before new account"
    savingsAcctNum = client.new_account('kurt', 'Savings')
    print "New savings account number: " + str(savingsAcctNum)
    print "Starting savings balance %s" % str(client.get_balance(savingsAcctNum))
    client.deposit(savingsAcctNum, 99999999)
    print "Confirming savings balance after deposit %s" % str(client.get_balance(savingsAcctNum))
    client.withdraw(savingsAcctNum, 1000)
    print "Confirming savings balance after withdrawl %s" % str(client.get_balance(savingsAcctNum))

    checkingAcctNum = client.new_account('kurt', 'Checking')
    print "New checking account number: " + str(checkingAcctNum)
    print "Starting checking balance %s" % str(client.get_balance(checkingAcctNum))
    client.deposit(checkingAcctNum, 99999999)
    print "Confirming checking balance after deposit %s" % str(client.get_balance(checkingAcctNum))
    client.withdraw(checkingAcctNum, 1000)
    print "Confirming checking balance after withdrawl %s" % str(client.get_balance(checkingAcctNum))

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

