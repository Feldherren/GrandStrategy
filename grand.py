import adventurelib # note: https://adventurelib.readthedocs.io/en/stable/
from adventurelib import *
import json
from pprint import pprint
import os
import sys
import logging
from datetime import datetime, timedelta
import calendar
from random import seed, randint

# TODO: consider linden city scenario
# map starts in tenuous control of the police
# police are allied with superheroes

# TODO: actions
# TODO: hiding; roll stealth, store result as state 'hiding: value'. Heroes can Search and roll Awareness; 

# TODO: don't really want to be throwing strings around except in user interaction; make everything use objects instead?
# at least have everything consisten (aside from user input, always going to be a string)

# TODO: automatically generate very simple map - numbers, paths (using - | \ /), and a key for where is where?
# command can be 'map'

# loading system strings
with open(os.path.join("data","strings.json")) as strings_json:
	strings_data = json.load(strings_json)

# language code; if you want more languages, add it to strings.json with a new code and change this, for the moment
# need a better language selection; can get available things from strings.json
# TODO: option to override terms in scenario.json?
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

seed()

agents = Bag()
known_agents = Bag()
regions = Bag()
factions = Bag()
units = Bag()
resources = Bag()

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

# TODO: not sure the way we get player resources is consistent
class Faction(Item):
	def about(self):
		say(self.name)
		say(self.desc)
	def status(self):
		say(self.name)
		# only show resources if player owns the faction
		# TODO: can find it out by spying, otherwise?
		if self == player_faction:
			for resource in self.resources:
				say(resources.find(resource).status())
		say(strings_data[language]["system"]["faction_locations_owned"])
		for location in self.locations:
			say(location)
		say(strings_data[language]["system"]["faction_agents_owned"])
		for agent in self.agents:
			say(agent)

class Agent(Item):
	def about(self):
		say(self.name)
		say(self.desc)
	def status(self):
		say(self.name)
		say(strings_data[language]["system"]["agent_location"].format(self.location.name))
		if len(self.states) > 0:
			say("States:")
			for state in self.states:
				say(state)

	def executeOrder(self):
		if self.order == "hide":
			self.hide()
		if self.order == "search":
			self.search()
		self.order = None

	# TODO: remember to clear hiding status after appropriate actions
	# moving shouldn't clear it?
	def hide(self):
		result = roll(self.stats["stealth"])
		if get_context() == "playing_game.debug":
			say(strings_data[language]["system"]["action_roll_result"].format(self.name, "stealth", self.stats["stealth"], result))
		if agentIsOwned(player_faction, self):
			say(strings_data[language]["system"]["action_hiding"].format(self.name))
		self.states["hiding"] = result
		# TODO: omit agents that are hiding from area status text

	def search(self):
		result = roll(self.stats["investigation"])
		if get_context() == "playing_game.debug":
			say(strings_data[language]["system"]["action_roll_result"].format(self.name, "investigation", self.stats["investigation"], result))
		if agentIsOwned(player_faction, self):
			say(strings_data[language]["system"]["action_searching"].format(self.name, self.location))
		for agent in self.location.agents:
			if agent is not self:
				if "hiding" in agent.states:
					if result >= agent.states["hiding"]:
						say(strings_data[language]["system"]["action_searching_foundAgent"].format(self.name, agent.name, self.location))

# TODO: not sure the way we get player resources is consistent
class Resource(Item):
	def about(self):
		say(self.name + " (plural: " + self.plural + ")")
		say(self.desc)
	def status(self):
		if player_faction.resources[self.name] > 1 or player_faction.resources[self.name] < 1:
			term = self.plural
		else:
			term = self.name
		say(strings_data[language]["system"]["resource_amount"].format(player_faction.resources[self.name], term))

class Unit(Item):
	def about(self):
		say(self.name + " (plural: " + self.plural + ")")
		say(self.desc)
		say("Cost: ")
		for resource in self.cost:
			if self.cost[resource] > 1:
				say("{} {}".format(self.cost[resource], resources.find(resource).plural))
			else:
				say("{} {}".format(self.cost[resource], resources.find(resource).name))
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

		# setting up resources
		for resource in scenario_data["scenario"]["resources"]:
			resources.add(Resource(resource["name"],resource["plural"]))
			new_resource = resources.find(resource["name"])
			new_resource.plural = resource["plural"]
			new_resource.desc = resource["desc"]

		# setting up the amount of time '1 turn' takes; days, months and years are valid
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
				new_location.armies = Bag()
				new_location.agents = Bag()
			else:
				logging.error("when creating location " + location["name"] + " could not find region " + location["region"])

		# loading and setting up agents

		with open(os.path.join("data",scenario_data['scenario']["agents"])) as agent_json:
			agent_data = json.load(agent_json)

		for agent in agent_data["agents"]:
			agents.add(Agent(agent["name"], *agent["aliases"]))
			new_agent = agents.find(agent["name"])
			new_agent.desc = agent["desc"]
			new_agent.traits = agent["traits"]
			new_agent.stats = agent["stats"]
			new_agent.states = {}
			new_agent.inventory = Bag()
			new_agent.location = None
			new_agent.faction = None
			new_agent.order = None
			if "hidden" not in new_agent.traits:
				known_agents.add(new_agent)

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
			new_faction.resources = {}
			for resource in faction["starting_resources"]:
				new_faction.resources[resource] = faction["starting_resources"][resource]
			new_faction.locations = Bag()
			new_faction.armies = Bag()
			new_faction.agents = Bag()
			for agent in faction["starting_agents"]:
				a = agents.find(agent)
				a.faction = new_faction
				new_faction.agents.add(a)
				a.location = getLocation(faction["starting_agents"][agent])
				a.location.agents.add(a)
			for location in faction["starting_locations"]:
				new_faction.locations.add(getLocation(location))
			if faction["playable"]:
				playable_factions.add(new_faction)

		# loading and setting up units

		with open(os.path.join("data",scenario_data['scenario']["units"])) as unit_json:
			unit_data = json.load(unit_json)

		for unit in unit_data["units"]:
			units.add(Unit(unit["name"], unit["plural"]))
			new_unit = units.find(unit["name"])
			new_unit.name = unit["name"]
			new_unit.plural = unit["plural"]
			new_unit.desc = unit["desc"]
			new_unit.cost = {}
			for resource in unit["cost"]:
				new_unit.cost[resource] = unit["cost"][resource]
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

# sets the player in debug mode
# sounds like a cheat code; it's just a thing from Niven's books
# TODO: debug mode commands, and stuff
# currently just lets you use a command to set your faction whenever
# may need reapplying whenever?
@when("tee tee hatch nex ool", context="playing_game")
def toggleWizardMode():
	if get_context() == "playing_game.debug":
		set_context("playing_game.faction_leader") # TODO; if we add other subcontexts of playing_game, make sure this part sets it back properly
		say(strings_data[language]["system"]["debugMode_disabled"])
	else:
		set_context("playing_game.debug")
		say(strings_data[language]["system"]["debugMode_enabled"])

# TODO: confirm choice before starting play?
# TODO: option to not respect playable factions - for force-changing factions or something, debug mode?
@when('play FACTION', context="pregame.faction_choice")
@when('choose FACTION', context="pregame.faction_choice")
@when('debug play FACTION', context="playing_game.debug")
@when('debug choose FACTION', context="playing_game.debug")
def setPlayableFaction(faction):
	global playable_factions
	global player_faction
	if faction in factions:
		if get_context() != "playing_game.debug":
			if faction in playable_factions:
				player_faction = factions.find(faction)
				player_faction.player_controller = True
				say(player_faction.intro_text)
				set_context("playing_game.faction_leader")
			else:
				say(strings_data[language]["error_messages"]["factionSelect_fail_factionNotPlayable"].format(faction))
		else:
			player_faction.player_controller = False # assuming you may be using it from controlling another faction
			player_faction = factions.find(faction)
			player_faction.player_controller = True
			say(strings_data[language]["system"]["debugMode_switchFaction"].format(faction))
			set_context("playing_game.debug")
	else:
		say(strings_data[language]["error_messages"]["factionSelect_fail_factionNotFound"].format(faction))

# TODO: I don't like just using 'faction' for whatever the player can play. Should it be customisable?
# TODO: make sure everything that should be listed is listed here
# TODO: need to account for whether the player is aware of armies
# TODO: account for scenario-specific strings for things?
@when("list THING", context="playing_game")
def list(thing):
	if thing == "region" or thing == "regions":
		for region in regions:
			say(region)
	if thing == "location" or thing == "locations":
		for region in regions:
			for location in region.locations:
				say(location.name + " (" + region.name + ")")
	if thing == "faction" or thing == "factions":
		for faction in factions:
			say(faction)
	if thing == "resource" or thing == "resources":
		for resource in resources:
			say(resource)
	if thing == "unit" or thing == "units":
		for unit in units:
			say(unit)
	if thing == "army" or thing == "armies":
		for faction in factions:
			for army in faction.armies:
				say(army)
	if thing == "agent" or thing == "agents":
		for agent in known_agents:
			say(agent)

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
	if known_agents.find(thing) is not None:
		thingy = agents.find(thing)
	if units.find(thing) is not None:
		thingy = units.find(thing)
	if resources.find(thing) is not None:
		thingy = resources.find(thing)
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
	if known_agents.find(thing) is not None:
		thingy = agents.find(thing)
	if getArmy(thing) is not None:
		thingy = getArmy(thing)
	if resources.find(thing) is not None:
		thingy = resources.find(thing)
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
						affordable = True
						for resource in unit_recruited.cost:
							if player_faction.resources[resource] < unit_recruited.cost[resource]*amt:
								affordable = False
								say(strings_data[language]["error_messages"]["purchase_fail_notEnoughResource"].format(resource, unit_recruited.cost[resource], player_faction.resources[resource]))
						if affordable:
							if nameIsUnused(army, skip=["army"]):
								if getArmy(army) is None:
									# make an army
									target_army = makeArmy(player_faction, army, location)
									say(strings_data[language]["system"]["makeArmy_success"].format(army))
								else:
									# check army is at location
									target_army = getArmy(army)
								if target_army.location == getLocation(location):
									# remove resources used
									for resource in unit_recruited.cost:
										player_faction.resources[resource] -= unit_recruited.cost[resource]*amt
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
								say(strings_data[language]["error_messages"]["name_fail_alreadyInUse"].format(army))
					else:
						say(strings_data[language]["error_messages"]["recruit_fail_locationUnowned"].format(location))
				else:
					say(strings_data[language]["error_messages"]["recruit_fail_locationUnknown"].format(location))
	else:
		say(strings_data[language]["error_messages"]["recruit_fail_unrecognisedUnit"])

@when("merge ARMYA into ARMYB")
@when("combine ARMYA with ARMYB")
def merge_armies(armya, armyb):
	global player_faction
	army_1 = player_faction.armies.find(armya)
	if army_1 == None:
		say(strings_data[language]["error_messages"]["merge_fail_armyNotFound"].format(armya))
	army_2 = player_faction.armies.find(armyb)
	if nameIsUnused(armyb, skip=['army']):
		if army_2 == None:
			army_2 = makeArmy(player_faction, armyb, army_1.location)
			say(strings_data[language]["system"]["makeArmy_success"].format(armyb))
		if army_1.location == army_2.location:
			for unit in army_1.units:
				if unit in army_2.units:
					army_2.units[unit] += army_1.units[unit]
				else:
					army_2.units[unit] = army_1.units[unit]
				# and now just removing army1 from existence
				player_faction.armies.take(armya)
				say(strings_data[language]["system"]["mergeArmy_success"].format(armya,armyb))
		else:
			say(strings_data[language]["error_messages"]["merge_fail_locationDifference"].format(armya, armyb))
	else:
		say(strings_data[language]["error_messages"]["name_fail_alreadyInUse"].format(armyb))

# TODO: functions for coded things; this should just call those, instead of having all the code in this function.
# TODO: search
# TODO: move
# TODO: define basic things here but let users define extra actions through JSON; how to code response?
@when("order AGENT to ACTION")
def order(agent, action):
	global player_faction
	if agentIsOwned(player_faction, agent):
		a = player_faction.agents.find(agent)
		if action == "hide":
			a.order = "hide"
			say(strings_data[language]["system"]["agent_order_hide"].format(a, a.location))
		if action == "search":
			a.order = "search"
			say(strings_data[language]["system"]["agent_order_search"].format(a, a.location))
	else:
		say(strings_data[language]["error_messages"]["order_fail_agentNotOwned"].format(agent))

# waits for a specified period of time
# AI handling and execution of delayed stuff like orders needs to go here
@when("wait")
@when("advance time")
@when("pass time")
@when("pass")
def wait():
	# TODO: AI
	# executing orders
	for agent in agents:
		agent.executeOrder()
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
@when("debug info OPTION", context="playing_game.debug")
def debug(option):
	if option == "context":
		say(get_context())

# Utility functions
# mostly called by other things

# makes an army with a name at a location, for a faction; takes string name, Faction or string name faction, Location or string name location
# returns the new army
# TODO: see if check for duplicate name can be folded into this function, instead
def makeArmy(faction, name, location):
	new_army = None
	if type(faction) is Faction:
		owner_faction = faction
	else:
		owner_faction = factions.find(faction)
	if type(location) is Location:
		army_location = location
	else:
		army_location = getLocation(location)
	owner_faction.armies.add(Army(name))
	new_army = owner_faction.armies.find(name)
	new_army.units = {}
	new_army.location = army_location
	army_location.armies.add(new_army)
	return new_army

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
def agentIsOwned(faction,agent):
	if type(faction) is Faction:
		owner_faction = faction
	else:
		owner_faction = factions.find(faction)
	if type(agent) is Agent:
		a = agent
	else:
		a = agents.find(agent)
	if a.faction is owner_faction:
		return True
	return False

# takes a faction, an agent, returns True/False if owned or not
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

# takes a string name, searches all factions for an army with that name if it exists; otherwise returns None
def getArmy(army):
	for faction in factions:
		if faction.armies.find(army) is not None:
			return faction.armies.find(army)
	return None

# takes a string name, makes sure nothing is already using it
# skips any type in the []
# TODO: add ifs for skip, as necessary
def nameIsUnused(name, skip = []):
	unused = True
	if regions.find(name) is not None:
		unused = False
	for region in regions:
		if region.locations.find(name) is not None:
			unused = False
	if factions.find(name) is not None:
		unused = False
	if agents.find(name) is not None:
		unused = False
	if units.find(name) is not None:
		unused = False
	if resources.find(name) is not None:
		unused = False
	if "army" not in skip:
		if getArmy(name) is not None:
			unused = False
	return unused

def roll(dice, sides=6):
	total  = 0
	for i in range (0, dice):
		total += randint(1,sides)
	return total

# Loading data

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