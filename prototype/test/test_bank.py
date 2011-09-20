#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

import unittest

from prototype.bank import BankService

class Test_Bank(unittest.TestCase):

    def _do_test(self, bank):
        acctNum = bank.new_account('kurt', 'Savings')
        print "New account number: " + str(acctNum)
        print "Starting balance %s" % str(bank.get_balance(acctNum))
        bank.deposit(acctNum, 99999999)
        print "Confirming balance after deposit %s" % str(bank.get_balance(acctNum))
        bank.withdraw(acctNum, 1000)
        print "Confirming balance after withdrawl %s" % str(bank.get_balance(acctNum))
        acctList = bank.list_accounts('kurt')
        for acctObj in acctList:
            print "Account: " + str(acctObj)

    def test_non_persistent(self):
        self._do_test(BankService({}))

#    def test_persistent(self):
#        self.do_test(BankService(persistent=True))

if __name__ == "__main__":
    unittest.main()
    
