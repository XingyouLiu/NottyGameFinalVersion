import random
from typing import List, Tuple, Dict
from collection_of_cards import CollectionOfCards
from card import Card
import math
from itertools import combinations
from concurrent.futures import ThreadPoolExecutor


class Player:
    def __init__(self, name: str, is_human: bool = True):
        self.name = name
        self.is_human = is_human
        self.cards: List[Card] = []    

    def add_card(self, card: Card, position: Tuple[int, int] = (0, 0), animate: bool = False):
        card.set_position(position[0], position[1], animate=animate)
        self.cards.append(card)

    def remove_card(self, card: Card) -> Card:
        card_index = self.cards.index(card)
        removed_card = self.cards.pop(card_index)
        return removed_card

    def exist_valid_group(self) -> bool:
        collection = CollectionOfCards(self.cards)
        return collection.exist_valid_group()
    
    
    def is_valid_group(self, cards: List[Card]) -> bool:
        collection = CollectionOfCards(cards)
        return collection.is_valid_group()
    
    
    def largest_valid_group(self) -> List[Card]:
        collection = CollectionOfCards(self.cards)
        return collection.largest_valid_group()

    
    def all_valid_groups(self) -> List[List[Card]]:
        collection = CollectionOfCards(self.cards)
        return collection.all_valid_groups()
    

    def find_best_discard(self):
        collection = CollectionOfCards(self.cards)
        return collection.find_best_discard()
    
    
    def calculate_probability(self, game_state: Dict) -> Dict:
        """
        Returns: Dictionary: key: action types, value: probability to obtain valid group with the action
        Mathematical model and details can be found in Computer_Player_Strategies.md (the probability calculating method is the same as the one used in X-AGGRESSIVE strategy)
        """
        collection = CollectionOfCards(game_state['current_player'].cards.copy())
        probabilities = {}

        #Calculate probability of obtaining valid group when drawing from deck
        for draw_count in range(1, 4):
            valid_count = 0
            if draw_count == 1:       #Calculating probability of drawing 1 card
                for card in game_state['deck_cards']:
                    collection.collection.append(card)
                    if collection.exist_valid_group():
                        valid_count += 1
                    collection.collection.pop()
                probabilities[('draw', 1, None)] = valid_count / game_state['deck_size']

            else:                       #Calculating probability of drawing 2 and 3 cards. Use itertools.combinations to efficiently calculate the number of combinations and loop through all combinations
                combination_count = math.factorial(game_state['deck_size']) // (math.factorial(draw_count) * math.factorial(game_state['deck_size'] - draw_count))
                for combination in combinations(game_state['deck_cards'], draw_count):
                    for card in combination:      #For each combination, Temporarily add it to hand, check if there exists a valid group. If so, increment the counter, then remove the combination from the hand.
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        valid_count += 1
                    for card in combination:
                        collection.collection.pop()
                probabilities[('draw', draw_count, None)] = valid_count / combination_count #probability is the ratio of valid combinations to total combinations
        
        #Calculate probability of taking cards from other players
        for player in game_state['other_players']:
            valid_count = 0
            for card in player.cards:
                collection.collection.append(card)
                if collection.exist_valid_group():
                    valid_count += 1
                collection.collection.pop()
            probabilities[('take', None, player)] = valid_count / len(player.cards)

        probabilities[('pass', None, None)] = 0    #Probability of passing is always 0 (Note that probability will only be calculated when human doesn't have any valid group, that's why it's always 0)

        return probabilities
    

    def calculate_draw_expectation(self, draw_count: int, game_state: Dict) -> Tuple[Tuple, float]:
        """
        Returns: Tuple: (action ('draw'), draw_count, None), expected_hand_size_reduction_value)
        Mathematical model and details can be found in Computer_Player_Strategies.md (the expected value calculating method is the same as the one used in X-DEFENSIVE strategy)
        """
        collection = CollectionOfCards(game_state['current_player'].cards.copy())
        draw_expected_value = 0
        
        #When drawing 1 card, simply loop through all cards in the deck, 
        #temporarily add it to hand, check if there exists a valid group. If so, get the maximum discard count, multiplied by the probability of drawing this card, then remove the card from hand.
        if draw_count == 1: 
            for card in game_state['deck_cards']:
                collection.collection.append(card)
                if collection.exist_valid_group():
                    draw_expected_value += collection.find_best_discard_count() * 1 / game_state['deck_size']
                collection.collection.pop()
            return (('draw', 1, None), draw_expected_value - draw_count)
        
        #When drawing 2 or 3 cards, use itertools.combinations to calculate the number of combinations
        #The maximum discard count calculation (find_best_discard_count) is time-consuming, so it is not efficient to loop through all combinations.
        #Therefore, use Monte Carlo sampling to randomly sample a certain number of combinations and calculate the expected value, then estimate the total expected value.
        else:
            combination_count = math.factorial(game_state['deck_size']) // (math.factorial(draw_count) * math.factorial(game_state['deck_size'] - draw_count))
            
            parameter = 1     #Sampling ratio, the smaller the ratio, the more accurate the expected value, but the longer the calculation time.
            sample_list = []  #List of sampled combinations
            if combination_count > 2000:  
                parameter = combination_count // 1000
                sample_list = random.sample(list(combinations(game_state['deck_cards'], draw_count)), combination_count // parameter)    
                for combination in sample_list:
                    for card in combination:
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        draw_expected_value += collection.find_best_discard_count() * 1 / combination_count
                    for card in combination:
                        collection.collection.pop()
            else:                                             #If the number of combinations is less than 2000, simply loop through all combinations
                for combination in combinations(game_state['deck_cards'], draw_count):
                    for card in combination:
                        collection.collection.append(card)
                    if collection.exist_valid_group():
                        draw_expected_value += collection.find_best_discard_count() * 1 / combination_count
                    for card in combination:
                        collection.collection.pop()

            return (('draw', draw_count, None), draw_expected_value * parameter - draw_count)
        
        
    def calculate_take_expectations(self, game_state: Dict, target_player) -> Tuple[Tuple, float]:
        """
        Returns: Tuple: (action ('take'), None, target_player), expected_hand_size_reduction_value)
        Mathematical model and details can be found in Computer_Player_Strategies.md (the expected value calculating method is the same as the one used in X-DEFENSIVE strategy)
        """
        collection = CollectionOfCards(game_state['current_player'].cards.copy())

        take_expected_value = 0
        for card in target_player.cards:
            collection.collection.append(card)
            if collection.exist_valid_group():
                take_expected_value += collection.find_best_discard_count() * 1 / len(target_player.cards)
            collection.collection.pop()

        return (('take', None, target_player), take_expected_value - 1)
    

    def draw_expectation(self, game_state: Dict) -> Dict:
        """
        Returns: Dictionary: key: action type, value: (expected_value, draw_count, target_player) tuples
        draw_count is None for 'take' and 'pass' actions
        target_player is None for 'draw' and 'pass' actions
        """
        draw_expected_values = {}

        #Calculate expected value for drawing 1, 2, and 3 cards. Use ThreadPoolExecutor to calculate expected values in parallel.
        with ThreadPoolExecutor(max_workers=3) as executor:
            draw_futures = [
                executor.submit(self.calculate_draw_expectation, i, game_state)
                for i in range(1, 4)
            ]
            
            for future in draw_futures:
                action, value = future.result()
                draw_expected_values[action] = value
        
        return draw_expected_values
    

    def take_expectation(self, game_state: Dict) -> Dict:
        """
        Returns: Dictionary: key: action types, value: (expected_value, draw_count, target_player) tuples
        draw_count is None for 'take' and 'pass' actions
        target_player is None for 'draw' and 'pass' actions
        """
        take_expected_values = {}
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            take_futures = [
                executor.submit(
                    self.calculate_take_expectations, game_state, target_player) for target_player in game_state['other_players']
            ]

            for future in take_futures:
                action, value = future.result()
                take_expected_values[action] = value
                
        return take_expected_values


    def clear_selections(self):
        """Clear the selection status of all cards in hand"""
        for card in self.cards:
            card.selected = False
            card.hover = False
            card.invalid = False
