from datetime import date, datetime, timedelta
from pyhafas.types.fptf import Journey, Leg, Remark, Stopover

def timedelta_to_dict(item):
    return str(item) if item else '0:00:00'

# see https://gist.github.com/sungitly/3f75cb297572dace2937?permalink_comment_id=4211196#gistcomment-4211196
def to_dict(item):
    match item:
        #case dict():
        #    return {k: to_dict(v) for k, v in item.items()}
        #case object(__dict__=_):
        #    return {k: v for k, v in vars(item).items()}

        case list() | tuple():
            return [to_dict(x) for x in item]

        case Journey():
            return {
                "origin":        item.legs[ 0].origin.name,
                "departure":     item.legs[ 0].departure,
                "delay":         timedelta_to_dict(item.legs[ 0].departureDelay),
                "destination":   item.legs[-1].destination.name,
                "arrival":       item.legs[-1].arrival,
                "delay_arrival": timedelta_to_dict(item.legs[-1].arrivalDelay),
                "transfers":     len(item.legs) - 1,
                "duration":      str(item.duration),
                "canceled":      any([x.cancelled for x in item.legs]),
                "ontime":        not item.legs[ 0].departureDelay,
                "products":      ", ".join([x.name for x in item.legs if x.name is not None]),
                "legs":          to_dict(item.legs or []),
            } if item.legs else None

        case Leg():
            return {
                "origin":           item.origin.name,
                "departure":        item.departure,
                "platform":         item.departurePlatform,
                "delay":            timedelta_to_dict(item.departureDelay),
                "destination":      item.destination.name,
                "arrival":          item.arrival,
                "platform_arrival": item.arrivalPlatform,
                "delay_arrival":    timedelta_to_dict(item.arrivalDelay),
                "mode":             str(item.mode).lower()[5:],
                "name":             item.name,
                "canceled":         item.cancelled,
                "distance":         item.distance,
                "remarks":          to_dict(item.remarks or []),
                "stopovers":        to_dict(item.stopovers or []),
            }

        case Remark():
            return item.text

        case Stopover():
            return item.stop.name + (" (canceled)" if item.cancelled else "")

        case timedelta():
            return timedelta_to_dict(item)

        case None:
            return item

        case _:
            return str(item)
