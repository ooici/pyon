"""
Example service that simulates exercising bond trades,
which for now is nothing more than persisting an order
object in a trade log and responding to the caller in
the affirmative.
"""

from pyon.core.bootstrap import IonObject

from interface.services.itrade_service import BaseTradeService

class TradeService(BaseTradeService):

    def exercise(self, order={}):
        # Made up market price of bond
        bond_price = 1.56

        order_create_tuple = self.clients.resource_registry.create(order)

        # Create confirmation response object
        confirmation_info = {}
        confirmation_info["tracking_number"] = order_create_tuple[0]
        confirmation_info["status"] = "complete"
        if order.type == 'buy':
            confirmation_info["proceeds"] = order.cash_amount / bond_price
        else:
            confirmation_info["proceeds"] = order.bond_amount * bond_price

        confirmation_obj = IonObject("Confirmation", confirmation_info)

        return confirmation_obj
