from ParserV2 import Parser
import asyncio


async def main():
    async with Parser() as parser:
        exists: bool = parser.check_output_file_exists()
        if not exists:
            return
        result = await parser.get_all_shop_data()
        parser.write_to_json(result)


if __name__ == "__main__":
    asyncio.run(main())