WIFI_SSID = "calsci_office_testing"
WIFI_PASS = "calsci101"


CLIENT_ID    = "chat123"
AWS_ENDPOINT = "a39ceguroqaxzh-ats.iot.ap-south-1.amazonaws.com"


TOPIC_UP   = "devices/{}/data".format(CLIENT_ID)
TOPIC_DOWN = "device/{}/data".format(CLIENT_ID)


CERT_KEY_PATHS = {
   "cert_der": "/certs/cert.der",
   "key_der":  "/certs/private.der",
   "ca_der":   "/certs/AmazonRootCA1.der",
}
