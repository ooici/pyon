"""
Example service that provides basic banking functionality.
This service tracks customers and their accounts (checking or saving)
"""

from pyon.public import Container
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, NotFound
from pyon.datastore.datastore import DataStore
from pyon.net.endpoint import RPCClient
from pyon.util.log import log

from interface.services.ibank_service import IBankService, BaseBankService

class BankService(BaseBankService):

    def new_account(self, name='', account_type='Checking'):
        find_res = []
        try:
            find_res = self.clients.resource_registry.find([("type_", DataStore.EQUAL, "BankCustomer"), DataStore.AND, ("name", DataStore.EQUAL, name)])
            customer_info = find_res[0]
            customer_id = customer_info._id
        except NotFound:
            # New customer
            pass
        if len(find_res) == 0:
            # Create customer info entry
            customer_info = {}
            customer_info["name"] = name
            customer_obj = IonObject("BankCustomer", customer_info)
            customer_create_tuple = self.clients.resource_registry.create(customer_obj)
            customer_id = customer_create_tuple[0]

        # Create account entry
        account_info = {}
        account_info["account_type"] = account_type
        account_info["owner"] = customer_id
        account_obj = IonObject("BankAccount", account_info)
        account_create_tuple = self.clients.resource_registry.create(account_obj)
        account_id = account_create_tuple[0]

        return account_id

    def deposit(self, account_id=-1, amount=0.0):
        account_obj = self.clients.resource_registry.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        account_obj.cash_balance += amount
        self.clients.resource_registry.update(account_obj)
        return "Balance after cash deposit: %s" % (str(account_obj.cash_balance))

    def withdraw(self, account_id=-1, amount=0.0):
        account_obj = self.clients.resource_registry.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        if account_obj.cash_balance < amount:
            raise BadRequest("Insufficient funds")
        account_obj.cash_balance -= amount
        self.clients.resource_registry.update(account_obj)
        return "Balance after cash withdrawl: %s" % (str(account_obj.cash_balance))

    def get_balances(self, account_id=-1):
        account_obj = self.clients.resource_registry.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        return account_obj.cash_balance, account_obj.bond_balance

    def buy_bonds(self, account_id='', cash_amount=0.0):
        """
        Purchase the specified amount of bonds.  Check is first made
        that the cash account has sufficient funds.
        """
        account_obj = self.clients.resource_registry.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        if account_obj.cash_balance < cash_amount:
            raise BadRequest("Insufficient funds")

        # Create order object and call trade service
        order_info = {}
        order_info["type"] = "buy"
        order_info["on_behalf"] = account_obj.owner
        order_info["cash_amount"] = cash_amount
        order_obj = IonObject("Order", order_info)

        confirmation_obj = self.clients.trade.exercise(order_obj)

        if confirmation_obj.status == "complete":
            account_obj.cash_balance -= cash_amount
            account_obj.bond_balance += confirmation_obj.proceeds
            self.clients.resource_registry.update(account_obj)
            return "Balances after bond purchase: cash %f    bonds: %s" % (account_obj.cash_balance,account_obj.bond_balance)
        return "Bond purchase status is: %s" % confirmation_obj.status

    def sell_bonds(self, account_id='', quantity=0):
        """
        Sell the specified amount of bonds.  Check is first made
        that the account has sufficient bonds.
        """
        account_obj = self.clients.resource_registry.read(account_id)
        if account_obj is None:
            raise NotFound("Account %d does not exist" % account_id)
        if account_obj.bond_balance < quantity:
            raise BadRequest("Insufficient bonds")

        # Create order object and call trade service
        order_info = {}
        order_info["type"] = "sell"
        order_info["on_behalf"] = account_obj.owner
        order_info["bond_amount"] = quantity
        order_obj = IonObject("Order", order_info)

        confirmation_obj = self.clients.trade.exercise(order_obj)

        if confirmation_obj.status == "complete":
            account_obj.cash_balance += confirmation_obj.proceeds
            account_obj.bond_balance -= quantity
            self.clients.resource_registry.update(account_obj)
            return "Balances after bond sales: cash %f    bonds: %s" % (account_obj.cash_balance,account_obj.bond_balance)
        return "Bond sales status is: %s" % confirmation_obj.status

    def list_accounts(self, name=''):
        """
        Find all accounts (optionally of type) owned by user
        """
        try:
            customer_list = self.clients.resource_registry.find([("type_", DataStore.EQUAL, "BankCustomer"), DataStore.AND, ("name", DataStore.EQUAL, name)])
        except:
            log.error("No customers found!")
            return []
        customer_obj = customer_list[0]
        accounts = self.clients.resource_registry.find([("type_", DataStore.EQUAL, "BankAccount"), DataStore.AND, ("owner", DataStore.EQUAL, customer_obj._id)])
        return accounts

def start_server():
    """
    This method will start a server container.  We then
    request the container to start all services defined
    in the r2deploy.yml.  The container then waits for
    incoming requests.
    """
    container = Container()
    container.start() # :(
    container.start_rel_from_url("res/deploy/r2deploy.yml")
    print 'Server container started'

    container.serve_forever()

def start_client():
    """
    This method will start a container.  We then establish
    an RPC client endpoint to the Bank service and send
    a series of requests.
    """
    container = Container()
    ready = container.start()
    ready.get()
    print 'Client container started'

    client = RPCClient(node=container.node, name="bank", iface=IBankService)
    print 'RPC endpoint created'

    print 'Creating savings account'
    savingsAcctNum = client.new_account('kurt', 'Savings')
    print "New savings account number: " + str(savingsAcctNum)
    print "Starting savings balance %s" % str(client.get_balances(savingsAcctNum))
    client.deposit(savingsAcctNum, 99999999)
    print "Savings balance after deposit %s" % str(client.get_balances(savingsAcctNum))
    client.withdraw(savingsAcctNum, 1000)
    print "Savings balance after withdrawl %s" % str(client.get_balances(savingsAcctNum))

    print "Buying 1000 savings bonds"
    client.buy_bonds(savingsAcctNum, 1000)
    print "Savings balance after bond purchase %s" % str(client.get_balances(savingsAcctNum))

    checkingAcctNum = client.new_account('kurt', 'Checking')
    print "New checking account number: " + str(checkingAcctNum)
    print "Starting checking balance %s" % str(client.get_balances(checkingAcctNum))
    client.deposit(checkingAcctNum, 99999999)
    print "Confirming checking balance after deposit %s" % str(client.get_balances(checkingAcctNum))
    client.withdraw(checkingAcctNum, 1000)
    print "Confirming checking balance after withdrawl %s" % str(client.get_balances(checkingAcctNum))

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

