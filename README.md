# Smartthings Soundbar
Updated with self learning source algoritm, if it does not work originally, use the remote to switch source, wait X sec, change again, wait, and just continue to every source and it should work perfectly from there

This is a fork from 
https://github.com/defnone/Home-Assistant-custom-components-SmartThings-Soundbar
and
https://github.com/PiotrMachowski/Home-Assistant-custom-components-SmartThings-Soundbar


modified to make source selection work again, tested and working with digital HDMI1 HDMI2 on HW-Q910A
also included suport for setup from the home assistant ui instead of configuration.yml

If the source change is not working for you
the attributes needed to add support for your model is shown on the media_player entity
so open a issue here with the attributes 
soundbar_model: HW-Q910A
and a list of possible sources like this
source: HDMI1 , sbMode: "3"
source: HDMI2 , sbMode: "20"
source: digital , sbMode: "10"
source: wifi , sbMode: "25"
and i will add support for your model asap.
if im slow to respond send me a reminder on [discord](https://discord.com/users/1270815586162708623)


