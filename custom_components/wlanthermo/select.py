"""Select platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_PITMASTER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SelectEntity] = []

    @callback
    def _create_entities():
        """Create entities when data is available."""
        if not coordinator.data:
            return

        entities: list[SelectEntity] = []

        if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
            for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
                entities.append(WLANThermoPitmasterModeSelect(coordinator, idx))
                entities.append(WLANThermoPitmasterChannelSelect(coordinator, idx))

        async_add_entities(entities)

    if coordinator.data:
        _create_entities()
    else:
        # Wait for data
        unsub = None
        @callback
        def _data_received():
            """Handle first data."""
            nonlocal unsub
            if unsub:
                unsub()
                unsub = None
            _create_entities()

        unsub = coordinator.async_add_listener(_data_received)


class WLANThermoPitmasterModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster mode select."""

    _attr_options = ["off", "manual", "auto"]
    _attr_translation_key = "mode"

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_mode"
        )
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Mode"
        self._attr_icon = "mdi:list-status"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        typ = self._get_pm_data().get("typ")
        if typ in self._attr_options:
            return typ
        return None
        
    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get current data to construct full payload
        pm_data = self._get_pm_data()
        
        # Default values if data missing
        current_channel = pm_data.get("channel", 1)
        current_pid = pm_data.get("pid", 0)
        current_value = pm_data.get("value", 0)
        current_set = pm_data.get("set", 0)
        # current_typ is replaced by option
        
        # specific fix: API expects "set_color" sometimes? No, user snippet uses "set". 
        
        # Construct full payload object
        payload_obj = {
            "id": self._pm_idx,
            "channel": current_channel,
            "pid": current_pid,
            "value": current_value,
            "set": current_set,
            "typ": option
        }
        
        # Wrap in list
        payload = [payload_obj]
        
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        _LOGGER.debug(f"Writing Pitmaster {self._pm_idx} Mode to {option}. Topic: {topic}, Payload: {payload}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["typ"] = option
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}


class WLANThermoPitmasterChannelSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster channel select."""
    
    # Options: 1 to 8 (assuming 8 channels max for now, or dynamic?)
    # Ideally dynamic, but SelectEntity options must be list of strings.
    # We provide 8 channels. using "Channel 1", "Channel 2" etc might be nicer for UI, 
    # but internal API uses integer index (1-based?).
    # Let's use simple numbers "1", "2"... 
    # Or "Channel 1", "Channel 2". Let's use "Channel X".
    
    _attr_options = [f"Channel {i}" for i in range(1, 9)] # Channel 1 to 8
    
    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_channel"
        )
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Channel"
        self._attr_icon = "mdi:thermometer-lines"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        # API returns integer channel index (probably 1-based, check automation snippet)
        # Snippet: "channel": {{ ... + 1 }} -> implies API uses 1-based.
        channel_idx = self._get_pm_data().get("channel") # e.g. 1
        if channel_idx:
            return f"Channel {channel_idx}"
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Extract number from "Channel X"
        try:
            channel_num = int(option.split(" ")[1])
        except (IndexError, ValueError):
            _LOGGER.error(f"Could not parse channel number from option: {option}")
            return

        # Get current data to construct full payload
        pm_data = self._get_pm_data()
        
        current_typ = pm_data.get("typ", "off")
        current_pid = pm_data.get("pid", 0)
        current_value = pm_data.get("value", 0)
        current_set = pm_data.get("set", 0)
        # current_channel is replaced by channel_num

        # Construct full payload object
        payload_obj = {
            "id": self._pm_idx,
            "channel": channel_num,
            "pid": current_pid,
            "value": current_value,
            "set": current_set,
            "typ": current_typ
        }

        # Payload must be a list
        payload = [payload_obj]
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx} Channel to {channel_num} ({option}) on topic {topic}. Payload: {payload}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["channel"] = channel_num
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}
 
 c l a s s   W L A N T h e r m o P i t m a s t e r P r o f i l e S e l e c t ( C o o r d i n a t o r E n t i t y ,   S e l e c t E n t i t y ) :  
         " " " R e p r e s e n t a t i o n   o f   a   W L A N T h e r m o   P i t m a s t e r   P r o f i l e   s e l e c t . " " "  
  
         _ a t t r _ i c o n   =   " m d i : f a c e - m a n - p r o f i l e "  
  
         d e f   _ _ i n i t _ _ ( s e l f ,   c o o r d i n a t o r ,   p m _ i d x :   i n t )   - >   N o n e :  
                 " " " I n i t i a l i z e   t h e   s e l e c t   e n t i t y . " " "  
                 s u p e r ( ) . _ _ i n i t _ _ ( c o o r d i n a t o r )  
                 s e l f . _ p m _ i d x   =   p m _ i d x  
                 s e l f . _ a t t r _ u n i q u e _ i d   =   (  
                         f " { c o o r d i n a t o r . t o p i c _ p r e f i x } _ p i t m a s t e r _ { p m _ i d x } _ p r o f i l e "  
                 )  
                 s e l f . _ a t t r _ n a m e   =   f " { c o o r d i n a t o r . d e v i c e _ n a m e }   P i t m a s t e r   { p m _ i d x   +   1 }   P r o f i l e "  
                 #   G e n e r i c   p r o f i l e s   0 . . 4   ( 5   p r o f i l e s )   a s   f a l l b a c k   s i n c e   w e   d o n ' t   h a v e   n a m e s  
                 s e l f . _ a t t r _ o p t i o n s   =   [ f " P r o f i l e   { i } "   f o r   i   i n   r a n g e ( 5 ) ]  
  
         @ p r o p e r t y  
         d e f   c u r r e n t _ o p t i o n ( s e l f )   - >   s t r   |   N o n e :  
                 " " " R e t u r n   t h e   s e l e c t e d   e n t i t y   o p t i o n . " " "  
                 #   A P I   r e t u r n s   i n t e g e r   p i d   i n d e x  
                 p i d   =   s e l f . _ g e t _ p m _ d a t a ( ) . g e t ( " p i d " )  
                 i f   p i d   i s   n o t   N o n e   a n d   0   < =   p i d   <   5 :  
                         r e t u r n   f " P r o f i l e   { p i d } "  
                 e l i f   p i d   i s   n o t   N o n e :  
                           #   I f   P I D   i s   o u t   o f   o u r   0 - 4   r a n g e ,   w e   s h o u l d   p r o b a b l y   a d d   i t   o r   h a n d l e   i t .  
                           #   F o r   n o w ,   r e t u r n   f o r m a t t e d   s t r i n g   e v e n   i f   n o t   i n   _ o p t i o n s   ( H A   m i g h t   w a r n )  
                           #   B u t   b e t t e r   t o   s t i c k   t o   o p t i o n s .  
                           r e t u r n   N o n e  
                 r e t u r n   N o n e  
  
         @ p r o p e r t y  
         d e f   d e v i c e _ i n f o ( s e l f )   - >   D e v i c e I n f o :  
                 " " " R e t u r n   d e v i c e   i n f o . " " "  
                 r e t u r n   D e v i c e I n f o (  
                         i d e n t i f i e r s = { ( D O M A I N ,   f " { s e l f . c o o r d i n a t o r . t o p i c _ p r e f i x } _ p i t m a s t e r _ { s e l f . _ p m _ i d x } " ) } ,  
                         n a m e = f " { s e l f . c o o r d i n a t o r . d e v i c e _ n a m e }   P i t m a s t e r   { s e l f . _ p m _ i d x   +   1 } " ,  
                         v i a _ d e v i c e = ( D O M A I N ,   s e l f . c o o r d i n a t o r . t o p i c _ p r e f i x ) ,  
                         m a n u f a c t u r e r = " W L A N T h e r m o " ,  
                         m o d e l = " P i t m a s t e r " ,  
                 )  
  
         a s y n c   d e f   a s y n c _ s e l e c t _ o p t i o n ( s e l f ,   o p t i o n :   s t r )   - >   N o n e :  
                 " " " C h a n g e   t h e   s e l e c t e d   o p t i o n . " " "  
                 t r y :  
                         #   E x t r a c t   n u m b e r   f r o m   " P r o f i l e   X "  
                         p i d _ n u m   =   i n t ( o p t i o n . s p l i t ( "   " ) [ 1 ] )  
                 e x c e p t   ( I n d e x E r r o r ,   V a l u e E r r o r ) :  
                         _ L O G G E R . e r r o r ( f " C o u l d   n o t   p a r s e   P I D   n u m b e r   f r o m   o p t i o n :   { o p t i o n } " )  
                         r e t u r n  
  
                 #   G e t   c u r r e n t   d a t a   t o   c o n s t r u c t   f u l l   p a y l o a d  
                 p m _ d a t a   =   s e l f . _ g e t _ p m _ d a t a ( )  
                  
                 c u r r e n t _ t y p   =   p m _ d a t a . g e t ( " t y p " ,   " o f f " )  
                 c u r r e n t _ c h a n n e l   =   p m _ d a t a . g e t ( " c h a n n e l " ,   1 )  
                 #   c u r r e n t _ p i d   r e p l a c e d   b y   p i d _ n u m  
                 c u r r e n t _ v a l u e   =   p m _ d a t a . g e t ( " v a l u e " ,   0 )  
                 c u r r e n t _ s e t   =   p m _ d a t a . g e t ( " s e t " ,   0 )  
  
                 #   C o n s t r u c t   f u l l   p a y l o a d   o b j e c t  
                 p a y l o a d _ o b j   =   {  
                         " i d " :   s e l f . _ p m _ i d x ,  
                         " c h a n n e l " :   c u r r e n t _ c h a n n e l ,  
                         " p i d " :   p i d _ n u m ,  
                         " v a l u e " :   c u r r e n t _ v a l u e ,  
                         " s e t " :   c u r r e n t _ s e t ,  
                         " t y p " :   c u r r e n t _ t y p  
                 }  
  
                 p a y l o a d   =   [ p a y l o a d _ o b j ]  
                 t o p i c   =   f " { s e l f . c o o r d i n a t o r . t o p i c _ p r e f i x } / { T O P I C _ S E T _ P I T M A S T E R } "  
                  
                 _ L O G G E R . d e b u g ( f " S e t t i n g   P i t m a s t e r   { s e l f . _ p m _ i d x }   P r o f i l e   t o   { p i d _ n u m }   ( { o p t i o n } )   o n   t o p i c   { t o p i c } .   P a y l o a d :   { p a y l o a d } " )  
                 a w a i t   m q t t . a s y n c _ p u b l i s h ( s e l f . h a s s ,   t o p i c ,   j s o n . d u m p s ( p a y l o a d ) )  
                  
                 #   O p t i m i s t i c   u p d a t e  
                 s e l f . c o o r d i n a t o r . d a t a [ " p i t m a s t e r " ] [ " p m " ] [ s e l f . _ p m _ i d x ] [ " p i d " ]   =   p i d _ n u m  
                 s e l f . a s y n c _ w r i t e _ h a _ s t a t e ( )  
  
         d e f   _ g e t _ p m _ d a t a ( s e l f )   - >   d i c t :  
                 " " " G e t   p i t m a s t e r   d a t a . " " "  
                 i f   n o t   s e l f . c o o r d i n a t o r . d a t a   o r   " p i t m a s t e r "   n o t   i n   s e l f . c o o r d i n a t o r . d a t a :  
                         r e t u r n   { }  
                 p m s   =   s e l f . c o o r d i n a t o r . d a t a [ " p i t m a s t e r " ] . g e t ( " p m " ,   [ ] )  
                 i f   s e l f . _ p m _ i d x   <   l e n ( p m s ) :  
                         r e t u r n   p m s [ s e l f . _ p m _ i d x ]  
                 r e t u r n   { }  
 