from Parser import Parser
from typing import Dict, List
from FileWriter import Writer

import asyncio

BATCH_SIZE = 4
DELAY_BETWEEN_BATCHES = 5

async def main() -> None:
    """
    JSON output is that it has list for every shop (with info for every card)
    and then list that contains BATCH_SIZE amount of these shops in it
    (can be flatten with itertools.chain(...) method later if needed)
    """
    parser: Parser = Parser()

    shop_data: List[Dict[str, str]] = parser.get_leftside_menu_shop_urls()
    shop_count: int = len(shop_data)

    final_result = []
    for i in range(0, shop_count, BATCH_SIZE):
        batch = shop_data[i: i + BATCH_SIZE]

        tasks = [parser.send_request_async(shop["link"]) for shop in batch]
        responses = await asyncio.gather(*tasks)

        parse_tasks = [parser.parse_info(html, shop["shop_name"]) for html, shop in zip(responses, shop_data)]
        parsed_results = await asyncio.gather(*parse_tasks)

        final_result.append(parsed_results)

        print(f"\n------Group {i // BATCH_SIZE + 1} from ~{shop_count // BATCH_SIZE} completed! Waiting {DELAY_BETWEEN_BATCHES}s to start another one...")
        await asyncio.sleep(DELAY_BETWEEN_BATCHES)

    
    Writer.write_to_json(final_result, parser.final_json)
    print("\n\nParsed succesfully...\n\n")

if __name__ == "__main__":
    asyncio.run(main())
