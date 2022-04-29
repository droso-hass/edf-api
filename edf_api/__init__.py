import aiohttp
import async_timeout
import time
from typing import Tuple

from edf_api.models import ElecInfo
from edf_api.const import TIMEOUT, USER_AGENT
from edf_api.auth import EDFAuth

class EDFApi:
    """
    Class to handle data retreival
    """
    
    def __init__(self, session: aiohttp.ClientSession, access_token: str, refresh_token: str, expiration: int) -> None:
        """
        Constructor

        Args:
            session: an aiohttp session
            access_token: the access token (it can be outaded and will be renewed automatically)
            refresh_token: a valid refresh_token
            expiration: the expiration date of the access_token (timestamp in sec)
        """
        self._session = session
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._expiration = expiration

    async def _get_access_token(self, force=False) -> str:
        """
        Function to get and access_token and ensure that it is valid

        Args:
            force: set to true to force the token refresh

        Returns:
            a valid access_token
        """
        if self._expiration-5 < time.time() or force:
            auth = EDFAuth(self._session)
            self._access_token, self._refresh_token, self._expiration = await auth.get_token(refresh_token=self._refresh_token)
        return self._access_token
        
    def save_tokens(self) -> Tuple[str, str, str]:
        """
        Function to save the access_token (which may have changed), refresh_token and expiration date for future use

        Returns:
            the access token
            the refresh token
            the expiration timestamp of the access token
        """
        return (self._access_token, self._refresh_token, self._expiration)

    async def get_info(self, insee: str, pdl: str) -> ElecInfo:
        """
        Function to get the grid status for a specific insee code

        Args:
            insee: the INSEE code
            pdl: the PDL id
        Returns:
            an ElecInfo object        
        """
        async with async_timeout.timeout(TIMEOUT):
            response = await self._session.get(f"https://megacache-ifr.p.web-enedis.fr/v2/get-info-reseau?codeinsees={insee}&codepostaux=&pdl={pdl}&siret=&marche=PARTICULIER&siappelant=FRONTAL")
            req = await response.json()

        for i in range(len(req["listeCoupuresInfoReseau"])):
            if req["listeCoupuresInfoReseau"][i]["codeInsee"] == insee:
                return ElecInfo.from_json(req["listeCoupuresInfoReseau"][i], req["listeCrises"][i])
        return ElecInfo.no_outage()

    async def get_data(self, bp_num: str, pdl: str, start: str, end: str, retry: bool = False) -> dict:
        """
        Function to get the consumption data

        Args:
            bp_num: the business partner number
            pdl: the PDL id
            start: the start date for the retrieved data in YYYY-MM-DD format
            end: the end date for the retrieved data in YYYY-MM-DD format
            retry: (internal) used to know if this is the first call to this function or if this is a retry
        """
        tok = await self._get_access_token(retry)
        async with async_timeout.timeout(TIMEOUT):
            response = await self._session.get(f"https://api-edf.edelia.fr/api/v1/sites/-/load-curve?step=30&begin-date={start}&end-date={end}&withCost=true",
                headers={
                    "Authorization": f"Bearer {tok}",
                    "person-ext-id": bp_num,
                    "site-ext-id": pdl,
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "fr-FR",
                },
            )
            req = await response.json()
            
            if (("errorCode" in req and req["errorCode"] == "401") or ("status" in req and req["status"] == 401)) and not retry:
                # try to force the access_token refresh if
                return await self.get_data(bp_num, pdl, start, end, True)

        return req
