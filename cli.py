import re
import os
import json
import asyncio
import aiohttp

from edf_api import EDFApi, EDFAuth

USER_FILE = "user.json"

async def main():
    session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=1, force_close=True))

    if not os.path.exists(USER_FILE):
        auth = EDFAuth(session)

        link, code_verifier, state, nonce = auth.get_login_url()
        print("open this url in chrome")
        print(link)
        err = input("paste the 'Failed to launch' error from the js console: ")

        code = re.findall("code=(.{8}-.{4}-.{4}-.{4}-.{12})", err)
        resp_state = re.findall("&state=(.*)&client_id", err)
        if len(code) != 1 or len(resp_state) != 1:
            print("unable to extract code and/or state")
            exit()

        if resp_state[0] != state:
            print("invalid state")
            exit()

        access_token, refresh_token, expiration = await auth.get_token(
            code=code[0], code_verifier=code_verifier, nonce=nonce
        )
        accord_co, bp_num, address = await auth.get_person_data(access_token)
        valid, pdl = await auth.get_pdl(access_token, accord_co, bp_num)
        insee = await auth.get_insee(address)

        if not valid:
            print("you counter is not compatible")
            exit()

    else:
        with open(USER_FILE, "r") as f:
            conf = json.load(f)
            access_token = conf["access_token"]
            refresh_token = conf["refresh_token"]
            expiration = conf["expiration"]
            insee = conf["insee"]
            bp_num = conf["bp_num"]
            pdl = conf["pdl"]

    api = EDFApi(session, access_token, refresh_token, expiration, bp_num, pdl, insee)

    try:
        print("grid status:")
        print(await api.get_grid_info(insee, pdl))
    except:
        print("error")

    start = input("enter start date in YYYY-MM-DD format: ")
    end = input("enter end date in YYYY-MM-DD format: ")
    print(await api.get_elec_daily_data(start, end))
    
    start = input("enter start date in YYYY-MM format: ")
    end = input("enter end date in YYYY-MM format: ")
    print(await api.get_elec_monthly_data(start, end))
    
    start = input("enter start date in YYYY-MM format: ")
    end = input("enter end date in YYYY-MM format: ")
    print(await api.get_elec_monthly_data_similar_homes(start, end))

    with open(USER_FILE, "w") as f:
        access_token, refresh_token, expiration = api.save_tokens()
        json.dump(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expiration": expiration,
                "insee": insee,
                "bp_num": bp_num,
                "pdl": pdl,
            },
            f,
        )

    await session.close()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
