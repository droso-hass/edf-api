import aiohttp
import async_timeout
import random
import string
import hashlib
import base64
import time
from lxml import etree
import urllib.parse
from typing import Tuple

from edf_api.const import TIMEOUT, USER_AGENT
from edf_api.exc import InvalidNonceException
from edf_api.models import Address


class EDFAuth:
    """
    Class to handle authentication with the EDF APIs and retrieve essential data to use them
    """

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    def _gen_str(self, nb) -> str:
        """
        Generate a random string of x length
        Args:
            nb: the length of the generated string
        Returns:
            a random string
        """
        return "".join(random.choice(string.ascii_letters) for i in range(nb))

    def get_login_url(self, redirect: str="edfetmoiauth:/oauthcallback") -> Tuple[str, str, str, str]:
        """
        Function to generate a login url for the first connection
        Args:
            redirect: the redirection url for the login request
        Returns:
            the link to edf login portal
            the code_verifier associated with this request (to use when retreiving the token)
            the state associated with this request (to compare when the results of this request are received)
            the nonce associated with this request (to use when retreiving the token)
        """
        state = self._gen_str(22) + "." + self._gen_str(16)
        code_verifier = self._gen_str(86)
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("utf8")).digest())
            .decode("utf8")
            .rstrip("=")
        )
        apptrack = self._gen_str(198)
        nonce = self._gen_str(22)
        redir = urllib.parse.quote_plus(redirect, encoding="utf-8")
        url = f"https://espace-client.edf.fr/sso/oauth2/INTERNET/authorize?redirect_uri={redir}&client_id=EDFETMOI_Android&response_type=code&prompt=login&state={state}&code_challenge={code_challenge}&code_challenge_method=S256&apptrack={apptrack}&login=true&nonce={nonce}"
        return (url, code_verifier, state, nonce)

    async def get_token(self, code: str=None, code_verifier: str=None, nonce: str=None, refresh_token: str=None) -> Tuple[str, str, int]:
        """
        Function to retrieve the access and refresh token
        The token can be requested using a code (for the first login) or a refresh token
        For the first mode, you need to provide the code, code_verifier and nonce arguments
        For the second mode, you only need to provide the refresh_token

        Args:
            code: the code returned by the login url
            code_verifier: the code returned by the get_login_url function
            nonce: the nonce returned by the get_login_url function
            refresh_token: the refresh_token to use to request a new access_token
        Returns:
            the new access_token
            the refresh_token (same as the one in argument if specified)
            the expiration date of the access_token
        """
        if code is not None and code_verifier is not None:
            data = {
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "edfetmoiauth:/oauthcallback",
                "code_verifier": code_verifier,
            }
        elif refresh_token is not None:
            data = {
                "grant_type": "refresh_token",
                "redirect_uri": "edfetmoiauth:/oauthcallback",
                "refresh_token": refresh_token
            }
        else:
            return (None, None, None)


        async with async_timeout.timeout(TIMEOUT):
            response = await self._session.post(
                "https://espace-client.edf.fr/sso/oauth2/INTERNET/access_token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "Authorization": "Basic RURGRVRNT0lfQW5kcm9pZDo=",
                },
                data=data,
            )
            req = await response.json()

        if code_verifier is not None and nonce != req["nonce"]:
            raise InvalidNonceException("invalid nonce")
            
        return (req["access_token"], req.get("refresh_token") or refresh_token, time.time()+req["expires_in"])

    async def get_person_data(self, access_token: str) -> Tuple[str, str, Address]:
        """
        Function to retrieve information related to the user

        Args:
            access_token: a valid access_token
        Returns:
            the contract agreement number
            the business partner number
            the address of the user
        """

        data = """
        <tns:listerContratClientParticulier_Request xmlns:tns="http://www.edf.fr/commerce/psc/0221/listerContratClientParticulier/v4">
            <situationUsage>EDFETMOI_Android</situationUsage>
            <SynchroniserSI>true</SynchroniserSI>
        </tns:listerContratClientParticulier_Request>
        """
        async with async_timeout.timeout(TIMEOUT):
            req = await self._session.post(
                "https://api-particuliers.edf.com/ws/listerContratClientParticulier_rest_V4-0/invoke",
                data=data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "fr-FR",
                    "Content-Type": "text/xml; charset=UTF-8",
                },
            )
            tree = etree.fromstring(await req.text())

        p = tree.xpath(
            "/tns:listerContratClientParticulier_Response/DonneesRetour/AccordCo",
            namespaces={
                "tns": "http://www.edf.fr/commerce/psc/0221/listerContratClientParticulier/v4"
            },
        )[0]

        return (p.xpath("Numero")[0].text, p.xpath("BP/Numero")[0].text, Address.from_xml(p.xpath("BP/AdressePartenaire")[0]))

    async def get_pdl(self, access_token:str, accord_co:str, numero_bp:str) -> Tuple[bool, str]:
        """
        Function to retrieve the PDL number and to check if the counter status

        Args:
            access_token: a valid access_token
            accord_co: the contract agreement number (from get_person_data)
            numero_bp: the business partner number (from get_person_data)
        Returns:
            the status of the counter: True if it is capable of reporting mesaurements, else False
            the PDL number of the counter
        """
        data = f"""
        <ns1:getDeploiementLinky_Request xmlns:ns1="http://www.edf.fr/psc/0289/getDeploiementLinky/v1">
            <ns1:jeton></ns1:jeton>
            <ns1:numeroBp>{numero_bp}</ns1:numeroBp>
            <ns1:accordCo>{accord_co}</ns1:accordCo>
        </ns1:getDeploiementLinky_Request>
        """
        async with async_timeout.timeout(TIMEOUT):
            req = await self._session.post(
                "https://api-particuliers.edf.com/ws/getDeploiementLinky_rest_V1-0/invoke",
                data=data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "fr-FR",
                    "Content-Type": "text/xml; charset=UTF-8",
                },
            )
            tree = etree.fromstring(await req.text())

        ns = {"tns": "http://www.edf.fr/psc/0289/getDeploiementLinky/v1"}
        p = tree.xpath(
            "/tns:getDeploiementLinky_Response/tns:DonneesRetour", namespaces=ns
        )[0]
        return (
            p.xpath("tns:statut", namespaces=ns)[0].text == "communiquant",
            p.xpath("tns:PDL", namespaces=ns)[0].text,
        )

    async def get_insee(self, addr: Address) -> str:
        """
        Function to retrieve the INSEE code from an address
        Args:
            addr: an address object
        Returns:
            the insee code
        """
        async with async_timeout.timeout(TIMEOUT):
            req = await self._session.get(f"https://geo.api.gouv.fr/communes?codePostal={addr.postal_code}&nom={addr.city}&fields=code&format=json&geometry=centre")
            j = await req.json()
        return j[0]["code"]

