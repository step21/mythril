"""This module contains the detection code for unauthorized ether
withdrawal."""
import logging
import json
from copy import copy

from mythril.analysis import solver
from mythril.analysis.modules.base import DetectionModule
from mythril.analysis.report import Issue
from mythril.analysis.swc_data import UNPROTECTED_ETHER_WITHDRAWAL
from mythril.exceptions import UnsatError
from mythril.laser.ethereum.state.global_state import GlobalState
from mythril.laser.smt import UGT, BVAddNoOverflow, Sum, symbol_factory

log = logging.getLogger(__name__)

DESCRIPTION = """

Search for cases where Ether can be withdrawn to a user-specified address. 

An issue is reported if:

- The transaction sender does not match contract creator;
- The sender address can be chosen arbitrarily;
- The receiver address is identical to the sender address;
- The sender can withdraw *more* than the total amount they sent over all transactions.

"""


class EtherThief(DetectionModule):
    """This module search for cases where Ether can be withdrawn to a user-
    specified address."""

    def __init__(self):
        """"""
        super().__init__(
            name="Ether Thief",
            swc_id=UNPROTECTED_ETHER_WITHDRAWAL,
            description=DESCRIPTION,
            entrypoint="callback",
            pre_hooks=["CALL"],
        )
        self._cache_addresses = {}

    def reset_module(self):
        """
        Resets the module by clearing everything
        :return:
        """
        super().reset_module()
        self._cache_addresses = {}

    def execute(self, state: GlobalState):
        """

        :param state:
        :return:
        """
        self._issues.extend(self._analyze_state(state))
        return self.issues

    def _analyze_state(self, state):
        """

        :param state:
        :return:
        """
        instruction = state.get_current_instruction()
        node = state.node

        if instruction["opcode"] != "CALL":
            return []

        address = instruction["address"]
        if self._cache_addresses.get(address, False):
            return []
        call_value = state.mstate.stack[-3]
        target = state.mstate.stack[-2]

        eth_sent_total = symbol_factory.BitVecVal(0, 256)

        constraints = copy(node.constraints)

        for tx in state.world_state.transaction_sequence:
            if tx.caller == 0xDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF:
                # There's sometimes no overflow check on balances added.
                # But we don't care about attacks that require more 2^^256 ETH to be sent.

                constraints += [BVAddNoOverflow(eth_sent_total, tx.call_value, False)]
                eth_sent_total = Sum(eth_sent_total, tx.call_value)
        constraints += [
            UGT(call_value, eth_sent_total),
            target == state.environment.sender,
        ]

        try:

            transaction_sequence = solver.get_transaction_sequence(state, constraints)

            debug = json.dumps(transaction_sequence, indent=4)

            issue = Issue(
                contract=node.contract_name,
                function_name=node.function_name,
                address=instruction["address"],
                swc_id=UNPROTECTED_ETHER_WITHDRAWAL,
                title="Unprotected Ether Withdrawal",
                severity="High",
                bytecode=state.environment.code.bytecode,
                description_head="Anyone can withdraw ETH from the contract account.",
                description_tail="Arbitrary senders other than the contract creator can withdraw ETH from the contract"
                + " account without previously having sent an equivalent amount of ETH to it. This is likely to be"
                + " a vulnerability.",
                debug=debug,
                gas_used=(state.mstate.min_gas_used, state.mstate.max_gas_used),
            )
        except UnsatError:
            log.debug("[ETHER_THIEF] no model found")
            return []

        self._cache_addresses[address] = True

        return [issue]


detector = EtherThief()
