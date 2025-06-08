import os
import json
import datetime
import requests
from julep import Client
from pprint import pprint
import googlemaps
import yaml

OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
MAPS_API_KEY = os.getenv('MAPS_API_KEY')
JULEP_API_KEY = os.getenv('JULEP_API_KEY')

def getWeatherDetails(city: str) -> dict:
    """
    Gets a 3-Hour forecast for the next 24 hours and returns a dictionary containing the key-value pairs which contains the information about the weather for different parts of the day.
    """
    baseUrl = "http://api.openweathermap.org/data/2.5/forecast?"
    Url = baseUrl + "appid=" + OPENWEATHER_API_KEY + "&q=" + city + "&units=metric"

    try:
        response = requests.get(Url)
        response.raise_for_status()
        forecastData = response.json()
        if forecastData.get('cod') != '200':
            return {}
        cityName = forecastData['city']['name']
        now = datetime.datetime.now()
        
        todayMorningForecast = None
        todayLunchForecast = None
        todayEveningForecast = None
        for forecast in forecastData['list']:
            forecastTime = datetime.datetime.fromtimestamp(forecast['dt'])
            if forecastTime > now and forecastTime < now + datetime.timedelta(hours = 24):
                if forecastTime.hour >= 7 and forecastTime.hour < 12 and not todayMorningForecast:
                    todayMorningForecast = forecast
                if forecastTime.hour >= 12 and forecastTime.hour < 17 and not todayLunchForecast:
                    todayLunchForecast = forecast
                if forecastTime.hour >= 18 and forecastTime.hour < 23 and not todayEveningForecast:
                    todayEveningForecast = forecast
        result = {
            'city' : cityName,
            'morning' : None,
            'lunch' : None,
            'evening' : None,
        }
        if todayMorningForecast:
            result['morning'] = {
                'temperatureInCelsius' : round(todayMorningForecast['main']['temp']),
                'condition' : todayMorningForecast['weather'][0]['description']
            }
        if todayLunchForecast:
            result['lunch'] = {
                'temperatureInCelsius' : round(todayLunchForecast['main']['temp']),
                'condition' : todayLunchForecast['weather'][0]['description']
            }
        if todayEveningForecast:
            result['evening'] = {
                'temperatureInCelsius' : round(todayEveningForecast['main']['temp']),
                'condition' : todayEveningForecast['weather'][0]['description']
            }
        return result


    except requests.exceptions.RequestException as e:
        return {'error' : f"Error connecting to Weather Service: {e}"}
    except KeyError as e:
        return {'error' : f"Unexpected data format from weather service. Missing key: {e}"}
    except Exception as e:
        return {'error' : f"Unexpected Error {e}"}
    
def findTopRestaurants(city: str, dishName: str) -> dict:
    """This Function is used to get top restaurants for a dish in a city"""
    MAPS_API_KEY = os.getenv('MAPS_API_KEY')

    try:
        gmaps = googlemaps.Client(key = MAPS_API_KEY)
        query = f"Best authentic {dishName} restaurants in {city}"

        print(f"---> Searching Google Maps for {query}")
        places = gmaps.places(query = query, language = 'en')

        if not places or not places.get('results'):
            return {'error' : f"No results found for '{dishName}' in {city}"}
        
        restaurants = []

        for place in places['results'][:3]:
            addressDict = place.get('address', {})
            restaurants.append({
                'name' : place.get('name'),
                'rating' : place.get('rating', 'N/A'),
                'address': addressDict.get('formatted_address', 'Address Not Available')
            })

        return {'restaurants' : restaurants}
    except Exception as e:
        return {"error": f"An unexpected error occurred with Google Maps API: {e}"}

def getIconicDish(city: str, meal_time: str) -> str:
    city_dishes = {
        'Hyderabad': {
            'breakfast': 'Pesarattu',
            'lunch': 'Hyderabadi Biryani',
            'dinner': 'Haleem'
        },
        'Mumbai': {
            'breakfast': 'Vada Pav',
            'lunch': 'Bombay Sandwich',
            'dinner': 'Pav Bhaji'
        },
        'Delhi': {
            'breakfast': 'Chole Bhature',
            'lunch': 'Butter Chicken',
            'dinner': 'Rajma Chawal'
        },
        'Chennai': {
            'breakfast': 'Idli',
            'lunch': 'Sambar Rice',
            'dinner': 'Dosa'
        }
    }
    return city_dishes.get(city, {}).get(meal_time, f"Famous {meal_time} dish")

toolsAvailable = {
        'getWeatherDetails' : getWeatherDetails,
        'findTopRestaurants' : findTopRestaurants,
        'getIconicDish': getIconicDish
        }

if __name__ == '__main__':
    print('---Initializing Setup---')
    client = Client(api_key = JULEP_API_KEY)

    weatherToolSchema = """
        name: getWeatherDetails
        description: Gets Weather Details of a city
        type: function
        function :
          parameters:
            type: object
            properties:
              city:
                type: string
                description: name of the city
    """

    restaurantFinderToolSchema = """
        name: findTopRestaurants
        description: gets the top restaurants containing the 'dishName' in a city
        type: function
        function: 
          parameters:
            type: object
            properties:
              city:
                type: string
                description: The city in which restaurants should be searched
              dishName:
                type: string
                description: The dish to be searched for

    """

    iconicDishToolSchema = """
        name: getIconicDish
        description: Gets the Iconic Dish for a city for a specific meal time
        type: function
        function:
          parameters:
            type: object
            properties:
              city:
                type: string
                description: The name of the city
              meal_time:
                type: string
                description: The Meal Time ( Breakfast, Lunch or Dinner)
    """
    
    try:
        agent = client.agents.create(
            name = 'AI Foodie Tour Agent',
            model = 'gpt-4o',
            about="Foodie Tour Generator Agent"
            )
        print("---Agent Created---")
        weather_tool = client.agents.tools.create(
        agent_id=agent.id,
        **yaml.safe_load(weatherToolSchema)
        )
        print(f"Created tool: {weather_tool.name}")
        restaurant_tool = client.agents.tools.create(
            agent_id=agent.id,
            **yaml.safe_load(restaurantFinderToolSchema)
        )
        print(f"Created tool: {restaurant_tool.name}")
        iconic_dish_tool = client.agents.tools.create(
            agent_id=agent.id,
            **yaml.safe_load(iconicDishToolSchema)
        )
        print(f"Created tool: {iconic_dish_tool.name}")
        tools = client.agents.tools.list(agent_id=agent.id)
        
        print("Registered tools:", [t.name for t in tools])
        print(agent)
        task = client.tasks.create(
            agent_id=agent.id,
            **yaml.safe_load("""
                name: Gets One Day Foodie Tour of the City     
                inherit_tools: true
                
                main:
                  - tool: getWeatherDetails
                    arguments:
                      city: "{{ inputs.city }}"
                  - tool: getIconicDish
                    name: breakfast_dish
                    arguments:
                      city: "{{ inputs.city }}"
                      meal_time: "breakfast"
                  - tool: getIconicDish
                    name: lunch_dish
                    arguments:
                      city: "{{ inputs.city }}"
                      meal_time: "lunch"
                  - tool: getIconicDish
                    name: dinner_dish
                    arguments:
                      city: "{{ inputs.city }}"
                      meal_time: "dinner"
                  - tool: findTopRestaurants
                    name: breakfast_spots
                    arguments:
                      city: "{{ inputs.city }}"
                      dishName: "{{ steps.breakfast_dish.output }}"
                  - tool: findTopRestaurants
                    name: lunch_spots
                    arguments:
                      city: "{{ inputs.city }}"
                      dishName: "{{ steps.lunch_dish.output }}"
                  - tool: findTopRestaurants
                    name: dinner_spots
                    arguments:
                      city: "{{ inputs.city }}"
                      dishName: "{{ steps.dinner_dish.output }}"           
            """)
        )
        print(f"Task '{task.name}' created Successfully")
    except Exception as e:
        print(f"Error creating Tasks {e}")
        exit()
    try:
        city_name = input("Enter the City: ")
        print(f"\n🚀 Running task for '{city_name}'... Julep is now handling the orchestration.")
        execution = client.executions.create(
            task_id=task.id,
            input={
                'city' : city_name
            }
        )
        while True:
            result = client.executions.get(execution.id)
            if result.status in ["succeeded", "failed"]:
                break
    except Exception as e:
        print(f"Error {e}")
        exit()
    print("\n========================================")
    print("✅ Task Execution Complete! Final Answer:")
    print("========================================")
    pprint(result)
