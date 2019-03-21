"""This module contains the detection code for predictable variable
dependence."""
import logging
import re

from mythril.analysis import solver
from mythril.analysis.call_helpers import get_call_from_state
from mythril.analysis.modules.base import DetectionModule
from mythril.analysis.ops import Call, VarType
from mythril.analysis.report import Issue
from mythril.analysis.swc_data import TIMESTAMP_DEPENDENCE, WEAK_RANDOMNESS
from mythril.exceptions import UnsatError
from mythril.laser.ethereum.state.global_state import GlobalState

log = logging.getLogger(__name__)


class PredictableDependenceModule(DetectionModule):
    """This module detects whether Ether is sent using predictable
    parameters."""

    def __init__(self) -> None:
        """"""
        super().__init__(
            name="Dependence of Predictable Variables",
            swc_id="{} {}".format(TIMESTAMP_DEPENDENCE, WEAK_RANDOMNESS),
            description=(
                "Check for CALLs that send >0 Ether as a result of computation "
                "based on predictable variables such as block.coinbase, "
                "block.gaslimit, block.timestamp, block.number"
            ),
            entrypoint="callback",
            pre_hooks=["CALL", "CALLCODE", "DELEGATECALL", "STATICCALL"],
        )

    def execute(self, state: GlobalState) -> list:
        """

        :param state:
        :return:
        """
        log.debug("Executing module: DEPENDENCE_ON_PREDICTABLE_VARS")
        self._issues.extend(_analyze_states(state))
        return self.issues


detector = PredictableDependenceModule()


def _analyze_states(state: GlobalState) -> list:
    """

    :param state:
    :return:
    """
    issues = []
    call = get_call_from_state(state)
    if call is None:
        return []
    if "callvalue" in str(call.value):
        log.debug("[DEPENDENCE_ON_PREDICTABLE_VARS] Skipping refund function")
        return []

    # We're only interested in calls that send Ether
    if call.value.type == VarType.CONCRETE and call.value.val == 0:
        return []

    address = call.state.get_current_instruction()["address"]

    description = (
        "The contract sends Ether depending on the values of the following variables:\n"
    )

    # First check: look for predictable state variables in node & call recipient constraints

    vars = ["coinbase", "gaslimit", "timestamp", "number"]
    found = []

    for var in vars:
        for constraint in call.node.constraints[:] + [call.to]:
            if var in str(constraint):
                found.append(var)

    if len(found):
        for item in found:
            description += "- block.{}\n".format(item)
        if solve(call):
            swc_id = TIMESTAMP_DEPENDENCE if item == "timestamp" else WEAK_RANDOMNESS

            description += (
                "Note that the values of variables like coinbase, gaslimit, block number and timestamp "
                "are predictable and/or can be manipulated by a malicious miner. "
                "Don't use them for random number generation or to make critical decisions."
            )

            issue = Issue(
                contract=call.node.contract_name,
                function_name=call.node.function_name,
                address=address,
                swc_id=swc_id,
                bytecode=call.state.environment.code.bytecode,
                title="Dependence on predictable environment variable",
                severity="Low",
                description_head="Sending of Ether depends on a predictable variable.",
                description_tail=description,
                gas_used=(
                    call.state.mstate.min_gas_used,
                    call.state.mstate.max_gas_used,
                ),
            )
            issues.append(issue)

    # Second check: blockhash

    for constraint in call.node.constraints[:] + [call.to]:
        if "blockhash" in str(constraint):
            if "number" in str(constraint):
                m = re.search(r"blockhash\w+(\s-\s(\d+))*", str(constraint))
                if m and solve(call):

                    found_item = m.group(1)

                    if found_item:  # block.blockhash(block.number - N)
                        description = (
                            "The predictable expression 'block.blockhash(block.number - "
                            + m.group(2)
                            + ")' is used to determine Ether recipient"
                        )
                        if int(m.group(2)) > 255:
                            description += (
                                ", this expression will always be equal to zero."
                            )
                    elif "storage" in str(
                        constraint
                    ):  # block.blockhash(block.number - storage_0)
                        description = (
                            "The predictable expression 'block.blockhash(block.number - "
                            + "some_storage_var)' is used to determine Ether recipient"
                        )
                    else:  # block.blockhash(block.number)
                        description = (
                            "The predictable expression 'block.blockhash(block.number)'"
                            + " is used to determine Ether recipient"
                        )
                        description += ", this expression will always be equal to zero."

                    issue = Issue(
                        contract=call.node.contract_name,
                        function_name=call.node.function_name,
                        address=address,
                        bytecode=call.state.environment.code.bytecode,
                        title="Dependence on Predictable Variable",
                        severity="Low",
                        description_head="Sending of Ether depends on the blockhash.",
                        description_tail=description,
                        swc_id=WEAK_RANDOMNESS,
                        gas_used=(
                            call.state.mstate.min_gas_used,
                            call.state.mstate.max_gas_used,
                        ),
                    )
                    issues.append(issue)
                    break
            else:

                r = re.search(r"storage_([a-z0-9_&^]+)", str(constraint))
                if r:  # block.blockhash(storage_0)

                    """We actually can do better here by adding a constraint
                    blockhash_block_storage_0 == 0 and checking model
                    satisfiability.

                    When this is done, severity can be raised from
                    'Informational' to 'Warning'. Checking that storage
                    at given index can be tainted is not necessary,
                    since it usually contains block.number of the
                    'commit' transaction in commit-reveal workflow.
                    """

                    index = r.group(1)
                    if index and solve(call):
                        description = (
                            "A block hash is calculated using the block.blockhash(uint blockNumber) method. "
                            "The block number is obtained from storage index {}".format(
                                index
                            )
                        )
                        issue = Issue(
                            contract=call.node.contract_name,
                            function_name=call.node.function_name,
                            address=address,
                            bytecode=call.state.environment.code.bytecode,
                            title="Dependence on Predictable Variable",
                            severity="Low",
                            description_head="Sending of Ether depends on the blockhash.",
                            description_tail=description,
                            swc_id=WEAK_RANDOMNESS,
                            gas_used=(
                                call.state.mstate.min_gas_used,
                                call.state.mstate.max_gas_used,
                            ),
                        )
                        issues.append(issue)
                        break
    return issues


def solve(call: Call) -> bool:
    """

    :param call:
    :return:
    """
    try:
        model = solver.get_model(call.node.constraints)
        log.debug("[DEPENDENCE_ON_PREDICTABLE_VARS] MODEL: " + str(model))
        pretty_model = solver.pretty_print_model(model)

        log.debug("[DEPENDENCE_ON_PREDICTABLE_VARS] main model: \n%s" % pretty_model)
        return True

    except UnsatError:
        log.debug("[DEPENDENCE_ON_PREDICTABLE_VARS] no model found")
        return False
