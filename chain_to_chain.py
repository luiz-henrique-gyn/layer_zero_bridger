import random
import asyncio
import argparse
import sys
from typing import Coroutine

from eth_typing import ChecksumAddress
from web3 import AsyncWeb3
from web3.contract import AsyncContract
from tqdm import tqdm

from config import PRIVATE_KEYS, AMOUNT_TO_SWAP
from modules.bridger import send_token_chain_to_chain, is_balance_updated
from modules.tokens import usdc, usdt
from modules.chains import polygon, avalanche, bsc, fantom
from modules.utils import get_correct_amount_and_min_amount, get_token_decimals, wallet_public_address
from modules.custom_logger import logger


async def chain_to_chain(
        wallet: str,
        from_chain_name: str,
        token: str,
        token_from_chain_contract: AsyncContract,
        to_chain_name: str,
        from_chain_w3: AsyncWeb3,
        destination_chain_id: int,
        source_pool_id: int,
        dest_pool_id: int,
        stargate_from_chain_contract: AsyncContract,
        stargate_from_chain_address: ChecksumAddress,
        from_chain_explorer: str,
        gas: int
) -> None:
    """Transfer function. It sends USDC from Polygon to Fantom.
    Stargate docs:  https://stargateprotocol.gitbook.io/stargate/developers

    Args:
        wallet:                         Wallet private key
        from_chain_name:                Sending chain name
        token:                          Token to be sent symbol
        token_from_chain_contract:      Sending chain token contract
        to_chain_name:                  Destination chain name
        from_chain_w3:                  Client
        destination_chain_id:           Destination chain id from stargate docs
        source_pool_id:                 Source pool id
        dest_pool_id:                   Destination pool id
        stargate_from_chain_contract:   Sending chain stargate router contract
        stargate_from_chain_address:    Address of Stargate Finance: Router at sending chain
        from_chain_explorer:            Sending chain explorer
        gas:                            Amount of gas
    """
    address = wallet_public_address(wallet)

    amount_to_swap, min_amount = await get_correct_amount_and_min_amount(token_contract=token_from_chain_contract,
                                                                         amount_to_swap=AMOUNT_TO_SWAP)

    start_delay = random.randint(1, 200)
    logger.info(f"START DELAY | {address} | Waiting for {start_delay} seconds.")
    with tqdm(
            total=start_delay, desc=f"Waiting START DELAY | {address}", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}"
    ) as pbar:
        for i in range(start_delay):
            await asyncio.sleep(1)
            pbar.update(1)

    balance = None
    logger_cntr = 0
    while not balance:
        await asyncio.sleep(30)
        if logger_cntr % 3 == 0:
            logger.info(f"BALANCE | {address} | Checking {from_chain_name} {token} balance")
        balance = await is_balance_updated(address=address, token=token, token_contract=token_from_chain_contract)
        logger_cntr += 1

    logger.info(
        f"BRIDGING | {address} | "
        f"Trying to bridge {amount_to_swap / 10 ** await get_token_decimals(token_from_chain_contract)} "
        f"{token} from {from_chain_name} to {to_chain_name}"
    )
    bridging_txn_hash = await send_token_chain_to_chain(
        wallet=wallet,
        from_chain_w3=from_chain_w3,
        transaction_info={
            "chain_id": destination_chain_id,
            "source_pool_id": source_pool_id,
            "dest_pool_id": dest_pool_id,
            "refund_address": address,
            "amount_in": amount_to_swap,
            "amount_out_min": min_amount,
            "lz_tx_obj": [
                0,
                0,
                "0x0000000000000000000000000000000000000001"
            ],
            "to": address,
            "data": "0x"
        },
        stargate_from_chain_contract=stargate_from_chain_contract,
        stargate_from_chain_address=stargate_from_chain_address,
        token_from_chain_contract=token_from_chain_contract,
        from_chain_name=from_chain_name,
        token=token,
        amount_to_swap=amount_to_swap,
        from_chain_explorer=from_chain_explorer,
        gas=gas
    )
    logger.success(
        f"{from_chain_name} | {address} | Transaction: https://{from_chain_explorer}/tx/{bridging_txn_hash.hex()}"
    )
    logger.success(f"LAYERZEROSCAN | {address} | Transaction: https://layerzeroscan.com/tx/{bridging_txn_hash.hex()}")


async def main():
    parser = argparse.ArgumentParser(
        description="Optional use case. Bridge tokens from one chain to another once for specified wallets."
    )

    mode_mapping = {
        "pf": "polygon-fantom",
        "pa": "polygon-avalanche",
        "pb": "polygon-bsc",
        "fp": "fantom-polygon",
        "fa": "fantom-avalanche",
        "fb": "fantom-bsc",
        "ap": "avalanche-polygon",
        "af": "avalanche-fantom",
        "ab": "avalanche-bsc",
        "bp": "bsc-polygon",
        "bf": "bsc-fantom",
        "ba": "bsc-avalanche",
    }

    parser.add_argument(
        "--mode",
        type=str,
        choices=mode_mapping.keys(),
        help="Bridging mode"
    )

    args = parser.parse_args()
    if args.mode is None:
        print("Error: the --mode argument is required")
        sys.exit(2)

    mode = mode_mapping[args.mode]

    tasks: list[Coroutine] = []
    for wallet in PRIVATE_KEYS:
        match mode:
            case "polygon-fantom":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=polygon.name,
                        token=usdc.name,
                        token_from_chain_contract=polygon.usdc_contract,
                        to_chain_name=fantom.name,
                        from_chain_w3=polygon.w3,
                        destination_chain_id=fantom.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=polygon.stargate_contract,
                        stargate_from_chain_address=polygon.stargate_address,
                        from_chain_explorer=polygon.explorer,
                        gas=polygon.gas
                    )
                )
            case "polygon-avalanche":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=polygon.name,
                        token=usdc.name,
                        token_from_chain_contract=polygon.usdc_contract,
                        to_chain_name=avalanche.name,
                        from_chain_w3=polygon.w3,
                        destination_chain_id=avalanche.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=polygon.stargate_contract,
                        stargate_from_chain_address=polygon.stargate_address,
                        from_chain_explorer=polygon.explorer,
                        gas=polygon.gas
                    )
                )
            case "polygon-bsc":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=polygon.name,
                        token=usdc.name,
                        token_from_chain_contract=polygon.usdc_contract,
                        to_chain_name=bsc.name,
                        from_chain_w3=polygon.w3,
                        destination_chain_id=bsc.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdt.stargate_pool_id,
                        stargate_from_chain_contract=polygon.stargate_contract,
                        stargate_from_chain_address=polygon.stargate_address,
                        from_chain_explorer=polygon.explorer,
                        gas=polygon.gas
                    )
                )
            case "fantom-polygon":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=fantom.name,
                        token=usdc.name,
                        token_from_chain_contract=fantom.usdc_contract,
                        to_chain_name=polygon.name,
                        from_chain_w3=fantom.w3,
                        destination_chain_id=polygon.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=fantom.stargate_contract,
                        stargate_from_chain_address=fantom.stargate_address,
                        from_chain_explorer=fantom.explorer,
                        gas=fantom.gas
                    )
                )
            case "fantom-avalanche":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=fantom.name,
                        token=usdc.name,
                        token_from_chain_contract=fantom.usdc_contract,
                        to_chain_name=avalanche.name,
                        from_chain_w3=fantom.w3,
                        destination_chain_id=avalanche.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=fantom.stargate_contract,
                        stargate_from_chain_address=fantom.stargate_address,
                        from_chain_explorer=fantom.explorer,
                        gas=fantom.gas
                    )
                )
            case "fantom-bsc":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=fantom.name,
                        token=usdc.name,
                        token_from_chain_contract=fantom.usdc_contract,
                        to_chain_name=bsc.name,
                        from_chain_w3=fantom.w3,
                        destination_chain_id=bsc.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdt.stargate_pool_id,
                        stargate_from_chain_contract=fantom.stargate_contract,
                        stargate_from_chain_address=fantom.stargate_address,
                        from_chain_explorer=fantom.explorer,
                        gas=fantom.gas
                    )
                )
            case "avalanche-polygon":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=avalanche.name,
                        token=usdc.name,
                        token_from_chain_contract=avalanche.usdc_contract,
                        to_chain_name=polygon.name,
                        from_chain_w3=avalanche.w3,
                        destination_chain_id=polygon.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=avalanche.stargate_contract,
                        stargate_from_chain_address=avalanche.stargate_address,
                        from_chain_explorer=avalanche.explorer,
                        gas=avalanche.gas
                    )
                )
            case "avalanche-fantom":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=avalanche.name,
                        token=usdc.name,
                        token_from_chain_contract=avalanche.usdc_contract,
                        to_chain_name=fantom.name,
                        from_chain_w3=avalanche.w3,
                        destination_chain_id=fantom.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=avalanche.stargate_contract,
                        stargate_from_chain_address=avalanche.stargate_address,
                        from_chain_explorer=avalanche.explorer,
                        gas=avalanche.gas
                    )
                )
            case "avalanche-bsc":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=avalanche.name,
                        token=usdc.name,
                        token_from_chain_contract=avalanche.usdc_contract,
                        to_chain_name=bsc.name,
                        from_chain_w3=avalanche.w3,
                        destination_chain_id=bsc.layer_zero_chain_id,
                        source_pool_id=usdc.stargate_pool_id,
                        dest_pool_id=usdt.stargate_pool_id,
                        stargate_from_chain_contract=avalanche.stargate_contract,
                        stargate_from_chain_address=avalanche.stargate_address,
                        from_chain_explorer=avalanche.explorer,
                        gas=avalanche.gas
                    )
                )
            case "bsc-polygon":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=bsc.name,
                        token=usdt.name,
                        token_from_chain_contract=bsc.usdt_contract,
                        to_chain_name=polygon.name,
                        from_chain_w3=bsc.w3,
                        destination_chain_id=polygon.layer_zero_chain_id,
                        source_pool_id=usdt.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=bsc.stargate_contract,
                        stargate_from_chain_address=bsc.stargate_address,
                        from_chain_explorer=bsc.explorer,
                        gas=bsc.gas
                    )
                )
            case "bsc-fantom":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=bsc.name,
                        token=usdt.name,
                        token_from_chain_contract=bsc.usdt_contract,
                        to_chain_name=fantom.name,
                        from_chain_w3=bsc.w3,
                        destination_chain_id=fantom.layer_zero_chain_id,
                        source_pool_id=usdt.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=bsc.stargate_contract,
                        stargate_from_chain_address=bsc.stargate_address,
                        from_chain_explorer=bsc.explorer,
                        gas=bsc.gas
                    )

                )
            case "bsc-avalanche":
                tasks.append(
                    chain_to_chain(
                        wallet=wallet,
                        from_chain_name=bsc.name,
                        token=usdt.name,
                        token_from_chain_contract=bsc.usdt_contract,
                        to_chain_name=avalanche.name,
                        from_chain_w3=bsc.w3,
                        destination_chain_id=avalanche.layer_zero_chain_id,
                        source_pool_id=usdt.stargate_pool_id,
                        dest_pool_id=usdc.stargate_pool_id,
                        stargate_from_chain_contract=bsc.stargate_contract,
                        stargate_from_chain_address=bsc.stargate_address,
                        from_chain_explorer=bsc.explorer,
                        gas=bsc.gas
                    )
                )

    logger.info(f"Bridging {mode_mapping[args.mode]}.")
    await asyncio.gather(*tasks, return_exceptions=True)

    logger.success("*** FINISHED ***")


if __name__ == "__main__":
    asyncio.run(main())
