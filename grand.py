import adventurelib # note: https://adventurelib.readthedocs.io/en/stable/
from adventurelib import *
import json
from pprint import pprint
import os
import sys
import logging
from datetime import datetime

# TODO: don't really want to be throwing strings around except in user interaction; make everything use objects instead?
# at least have everything consisten (aside from user input, always going to be a string)

# loading system strings
with open(os.path.join("data","strings.json")) as strings_json:
	strings_data = json.load(strings_json)

# language code; if you want more languages, add it to strings.json with a new code and change this, for the moment
# need a better language selection; can get available things from strings.json
default_language = "en"
language = default_language # TODO: change this with a selection

# TODO: set up logging file

global player_faction

agents = Bag()
armies = Bag()
regions = Bag()
factions = Bag()
units = Bag()

class Region(Item):
	def about(self):
		say(self.name)
		say(self.desc)
		say("Contains:")
		for location in self.locations:
			say(location.name)
	def status(self):
		say(self.name)

class Location(Item):
	def about(self):
		say(self.name)
		say(self.desc)
	def status(self):
		say(self.name)

class Faction(Item):
	def about(self):
		say(self.name)
		say(self.desc)
	def status(self):
		global player_faction
		say(self.name)
		# only show money if player owns the faction
		# TODO: can find it out by spying, otherwise?
		if self == player_faction:
			say(scenario_data["scenario"]["money_term"] +  ": " + str(self.money))
		say(strings_data[language]["system"]["locations_owned"])
		for location in self.locations:
			say(location)

class Agent(Item):
	def about(self):
		say(self.name)
		say(self.desc)
	def status(self):
		say(self.name)

class Unit(Item):
	def about(self):
		say(self.name + " (plural: " + self.plural + ")")
		say(self.desc)
		say("Cost: " + str(self.cost))
		say("Health: " + str(self.health))
		say("Strength: " + str(self.strength))
		say("Stealth: " + str(self.stealth))

class Army(Item):
	def status(self):
		say(self.name)
		say("Stationed at " + self.location)
		say("Composition: ")
		for unit in self.units:
			say(unit + ": " + str(self.units[unit]))

# Game Command Functions

@when('about THING')
def about(thing):
	thingy = None
	if regions.find(thing) is not None:
		thingy = regions.find(thing)
	for region in regions:
		if region.locations.find(thing) is not None:
			thingy = region.locations.find(thing)
	if factions.find(thing) is not None:
		thingy = factions.find(thing)
	if agents.find(thing) is not None:
		thingy = agents.find(thing)
	if units.find(thing) is not None:
		thingy = units.find(thing)
	if thingy is not None:
		thingy.about()
	else:
		say(strings_data[language]["error_messages"]["about_fail_thingNotFound"].format(thing))

@when('status THING')
def status(thing):
	thingy = None
	if regions.find(thing) is not None:
		thingy = regions.find(thing)
	for region in regions:
		if region.locations.find(thing) is not None:
			thingy = region.locations.find(thing)
	if factions.find(thing) is not None:
		thingy = factions.find(thing)
	if agents.find(thing) is not None:
		thingy = agents.find(thing)
	if armies.find(thing) is not None:
		thingy = armies.find(thing)
	if thingy is not None:
		thingy.status()
	else:
		say(strings_data[language]["error_messages"]["status_fail_thingNotFound"].format(thing))

@when('recruit AMOUNT x UNIT at LOCATION to ARMY')
def recruit(amount, unit, location, army):
	global player_faction
	# check that the unit exists
	if units.find(unit) is not None:
		# store unit details for later
		unit_recruited = units.find(unit)
		# make sure AMOUNT is a valid number
		if(isRecruitable(unit)):
			amt = 0
			try:
				amt = int(amount)
			except ValueError:
				say(strings_data[language]["error_messages"]["recruit_fail_valueError"])
			if amt >= 1:
				# check location exists
				if getLocation(location) is not None:
					# check location is owned
					if (locationIsOwned(player_faction.name, location)):
						# check we can afford it
						cost = unit_recruited.cost * amt
						if player_faction.money >= cost:
							if army not in armies:
								# make an army
								armies.add(Army(army))
								target_army = armies.find(army)
								target_army.units = {}
								target_army.location = location
							else:
								# check army is at location
								target_army = armies.find(army)
							if target_army.location is location:
								# remove cost
								player_faction.money -= cost
								# add units to existing army
								if unit in target_army.units:
									target_army.units[unit] += amt
								else:
									target_army.units[unit] = amt
								if amt > 1:
									say(strings_data[language]["system"]["recruit_success"].format(amount, units.find(unit).plural, army, location))
								else:
									say(strings_data[language]["system"]["recruit_success"].format(amount, units.find(unit).name, army, location))
							else:
								say(strings_data[language]["error_messages"]["recruit_fail_armyNotAtLocation"].format(army, location))
						else:
							if amt > 1:
								say(strings_data[language]["error_messages"]["recruit_fail_notEnoughMoney"].format(amount, unit_recruited.plural))
							else:
								say(strings_data[language]["error_messages"]["recruit_fail_notEnoughMoney"].format(amount, unit_recruited.name))
					else:
						say(strings_data[language]["error_messages"]["recruit_fail_locationUnowned"].format(location))
				else:
					say(strings_data[language]["error_messages"]["recruit_fail_locationUnknown"].format(location))
	else:
		say(strings_data[language]["error_messages"]["recruit_fail_unrecognisedUnit"])

# Other Functions
# TODO: don't acknowledge values outside of the list
# TODO: can use context to make a proper command for choosing what to play
def chooseFaction(options):
	global player_faction
	i = 0
	for faction in options:
		print(str(i+1) + ": " + faction)
		i += 1
	say(strings_data[language]["system"]["choose_faction"])
	faction_choice = int(input("> "))-1
	player_faction = factions.find(options[faction_choice])
	player_faction.player_controller = True
	say(player_faction.intro_text)

# takes a string name of unit, returns True/False if recruitable or not
# TODO: add recruitability checks; factions, regions, locations and maybe improvements can affect this
# needs support in the JSON, though
def isRecruitable(unit):
	return True

# takes a string name of faction, string name of region, returns True/False if owned or not
# TODO: add ownership check
def regionIsOwned(faction,region):
	return False

# takes a string name of faction, string name of location, returns True/False if owned or not
def locationIsOwned(faction,location):
	fac = factions.find(faction)
	if location in fac.locations:
		return True
	return False

# takes a string name, gets a location with that name if it exists; otherwise returns None
def getLocation(location):
	found_location = None
	for region in regions:
		if region.locations.find(location) is not None:
			found_location = region.locations.find(location)
	return found_location

# Loading data
# TODO: remove requirement for scenarios.json, just find scenario.jsons below data dir

with open(os.path.join("data","scenarios.json")) as scenarios_json:
	scenarios_data = json.load(scenarios_json)

# TODO: choose scenario; just provide a menu here
# we're just going to assume base scenario, though
with open(os.path.join("data",scenarios_data['scenarios'][0]["scenario_json"])) as scenario_json:
	scenario_data = json.load(scenario_json)

# setting up start date
current_date = datetime(scenario_data["scenario"]["start_date"]["year"], scenario_data["scenario"]["start_date"]["month"], scenario_data["scenario"]["start_date"]["day"])

def prompt():
    return '{shown_date} > '.format(shown_date=current_date.strftime(scenario_data["scenario"]["date_format"]))

adventurelib.prompt = prompt

# loading and setting up game map

with open(os.path.join("data",scenario_data['scenario']["map"])) as map_json:
	map_data = json.load(map_json)

for region in map_data["regions"]:
	regions.add(Region(region["name"]))
	new_region = regions.find(region["name"])
	new_region.desc = region["desc"]
	new_region.locations = Bag()

for location in map_data["locations"]:
	if regions.find(location["region"]) is not None:
		region = regions.find(location["region"])
		region.locations.add(Location(location["name"]))
		new_location = region.locations.find(location["name"])
		new_location.desc = location["desc"]
	else:
		logging.error("when creating location " + location["name"] + " could not find region " + location["region"])

# loading and setting up factions

with open(os.path.join("data",scenario_data['scenario']["factions"])) as faction_json:
	faction_data = json.load(faction_json)

playable_factions = []

for faction in faction_data["factions"]:
	factions.add(Faction(faction["name"], *faction["aliases"]))
	new_faction = factions.find(faction["name"])
	new_faction.desc = faction["desc"]
	new_faction.intro_text = faction["intro_text"]
	new_faction.money = faction["starting_money"]
	new_faction.locations = Bag()
	for location in faction["starting_locations"]:
		new_faction.locations.add(getLocation(location))
	if faction["playable"]:
		playable_factions.append(faction["name"])

# loading and setting up agents

with open(os.path.join("data",scenario_data['scenario']["agents"])) as agent_json:
	agent_data = json.load(agent_json)

for agent in agent_data["agents"]:
	agents.add(Agent(agent["name"]))
	new_agent = agents.find(agent["name"])
	new_agent.desc = agent["desc"]

# loading and setting up units

with open(os.path.join("data",scenario_data['scenario']["units"])) as unit_json:
	unit_data = json.load(unit_json)

for unit in unit_data["units"]:
	units.add(Unit(unit["name"], unit["plural"]))
	new_unit = units.find(unit["name"])
	new_unit.name = unit["name"]
	new_unit.plural = unit["plural"]
	new_unit.desc = unit["desc"]
	new_unit.cost = unit["cost"]
	new_unit.strength = unit["strength"]
	new_unit.health = unit["health"]
	new_unit.stealth = unit["stealth"]

# TODO: interface for player choosing faction

chooseFaction(playable_factions)

#with open() as faction_json:
#	faction_data = json.load(faction_json)

#pprint(scenario_data)
# for scenario in scenario_data['scenarios']:
# 	print(scenario['name'])
# 	print(scenario['desc'])

start()