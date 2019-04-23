import adventurelib # note: https://adventurelib.readthedocs.io/en/stable/
from adventurelib import *
import json
from pprint import pprint
import os
import sys
import logging
from datetime import datetime, timedelta
import calendar

# TODO: don't really want to be throwing strings around except in user interaction; make everything use objects instead?
# at least have everything consisten (aside from user input, always going to be a string)

# TODO: automatically generate very simple map - numbers, paths (using - | \ /), and a key for where is where?
# command can be 'map'

# loading system strings
with open(os.path.join("data","strings.json")) as strings_json:
	strings_data = json.load(strings_json)

# language code; if you want more languages, add it to strings.json with a new code and change this, for the moment
# need a better language selection; can get available things from strings.json
default_language = "en"
language = default_language # TODO: change this with a selection

# TODO: set up logging file

global scenario_data
global current_date
current_date = datetime.now()
global wait_unit
global wait_period
global playable_factions
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

# function for setting scenario. Effectively the first thing the player does in a game, and leads into choosing faction.
# loads all the data; new json has to be loaded here
# seems to work fine without setting the Bags global; watch for any issues from this
@when('play SCENARIO', context="pregame.scenario_choice")
@when('choose SCENARIO', context="pregame.scenario_choice")
def setScenario(scenario):
	global scenarios
	global scenario_data
	global current_date
	global wait_unit
	global wait_period
	if scenario in scenarios:
		with open(scenarios[scenario]) as scenario_json:
			scenario_data = json.load(scenario_json)

		# setting up start date
		current_date = datetime(scenario_data["scenario"]["start_date"]["year"], scenario_data["scenario"]["start_date"]["month"], scenario_data["scenario"]["start_date"]["day"])

		# setting up the amount of time '1 turn' takes; currently takes days
		# TODO: some way of handling months, years
		wait_unit = scenario_data["scenario"]["time_step"]["unit"]
		wait_period = scenario_data["scenario"]["time_step"]["amount"]

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

		global playable_factions
		playable_factions = Bag()

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
				playable_factions.add(new_faction)

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

		set_context('pregame.faction_choice')
		for faction in playable_factions:
			say(faction.name)
		say(strings_data[language]["system"]["choose_faction"])

	else:
		say(strings_data[language]["error_messages"]["scenarioSelect_fail_scenarioNotFound"].format(scenario))

# Game Command Functions
# TODO: confirm choice before starting play?
# TODO: option to not respect playable factions - for force-changing factions or something, debug mode?
# not using just 'FACTION' as that blocks quit/help/any other commands
#@when('FACTION', context="pregame.faction_choice")
@when('play FACTION', context="pregame.faction_choice")
@when('choose FACTION', context="pregame.faction_choice")
def setPlayableFaction(faction):
	global playable_factions
	global player_faction
	if faction in factions:
		if faction in playable_factions:
			player_faction = factions.find(faction)
			player_faction.player_controller = True
			say(player_faction.intro_text)
			set_context("playing_game.faction_leader")
		else:
			say(strings_data[language]["error_messages"]["factionSelect_fail_factionNotPlayable"].format(faction))
	else:
		say(strings_data[language]["error_messages"]["factionSelect_fail_factionNotFound"].format(faction))

@when('about THING', context="playing_game")
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

@when('status THING', context="playing_game")
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

# TODO: really need a more natural way of separating AMOUNT and UNIT to prevent greediness
@when('recruit AMOUNT x UNIT at LOCATION to ARMY', context="playing_game")
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

# waits for a specified period of time
# AI handling and execution of delayed stuff like orders needs to go here
@when("wait")
@when("advance time")
@when("pass time")
@when("pass")
def wait():
	# advancing the date
	global current_date
	global wait_unit
	global wait_period
	if wait_unit == "day" or wait_unit == "days":
		current_date += timedelta(days=wait_period)
	elif wait_unit == "month" or wait_unit == "months":
		for x in range(0,wait_period):
			current_date += timedelta(calendar.monthrange(current_date.year, current_date.month)[1])
	elif wait_unit == "year" or wait_unit == "years":
		for x in range(0,wait_period):
			for y in range(0,12):
				current_date += timedelta(calendar.monthrange(current_date.year, current_date.month)[1])

# debug command
@when("debug OPTION")
def debug(option):
	if option == "context":
		say(get_context())

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
	for region in regions:
		if region.locations.find(location) is not None:
			return region.locations.find(location)
	return None

#def getUnit

# Loading data
# TODO: remove requirement for scenarios.json, just find scenario.jsons below data dir
# with open(os.path.join("data","scenarios.json")) as scenarios_json:
# 	scenarios_data = json.load(scenarios_json)

set_context('pregame.scenario_choice')
scenario_files = []
for root, dirs, files in os.walk("data"):
    if "scenario.json" in files:
        scenario_files.append(os.path.join(root, "scenario.json"))

global scenarios
scenarios = {}
for sc in scenario_files:
	with open(sc) as scenario_json:
		scenario_data = json.load(scenario_json)
		scenarios[scenario_data["scenario"]["name"].lower()] = sc

for scenario in scenarios:
	say(scenario)

say(strings_data[language]["system"]["choose_scenario"])


def prompt():
	global current_date
	if get_context() == "pregame.scenario_choice":
		return '> '
	else:
		return '{shown_date} > '.format(shown_date=current_date.strftime(scenario_data["scenario"]["date_format"]))

adventurelib.prompt = prompt

start()