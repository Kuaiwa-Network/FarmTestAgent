"""Bounded Scripted story 10 sequence. Six fixed steps; no tutorial actions."""
from farmqa_authenticated_fixture import authenticated_binding
from farmqa_story_navigation import StoryNavigationAdapter, StoryNavigationClient, story_observation

STEPS=(10,20,30,40,50,60)


def sequence_binding(raw):
    if not isinstance(raw,dict) or type(raw.get('story_step')) is not int or raw['story_step'] not in STEPS:
        raise ValueError('One of the six introductory story steps required')
    authenticated_binding({k:v for k,v in raw.items() if k!='story_step'})
    return dict(raw)


def sequence_observation(raw,action_id,binding):
    finishing=binding['story_step']==60
    finished=raw.get('outcome')=='finished'
    # Apply shared strict action/event validation without treating a missing story
    # view as proof of completion. The additional guide checks below are mandatory.
    checked=dict(raw)
    if finished:checked['outcome']='advanced';checked['story_step']=60
    result=story_observation(checked,action_id,binding,expected_step=binding['story_step'],
                             expected_next=60 if finishing else binding['story_step']+10)
    fields=('view','guide_group','guide_step','checkpoint_reached','dialogue_visible')
    if (any(k not in raw for k in fields) or raw['view'] not in ('StoryPlayView','MainView',None)
        or type(raw['guide_group']) is not int or type(raw['guide_step']) is not int
        or type(raw['checkpoint_reached']) is not bool or type(raw['dialogue_visible']) is not bool
        or finished and (not finishing or raw['story_step'] is not None or raw['view']!='MainView'
            or raw['guide_group']!=10 or raw['guide_step']!=2 or raw['checkpoint_reached'] or not raw['dialogue_visible'])
        or raw.get('outcome')=='advanced' and (finishing or raw['view']!='StoryPlayView'
            or raw['guide_group']!=10 or raw['guide_step']!=1 or raw['checkpoint_reached'])):
        raise ValueError('Missing or inconsistent sequence outcome')
    return {**result,**{k:raw[k] for k in fields},'story_step':raw['story_step'],'outcome':raw['outcome']}


class StorySequenceClient(StoryNavigationClient):
    _binding=staticmethod(sequence_binding)

    def _story_parameters(self,binding):
        step=binding['story_step']
        return {'STORY_STEP':str(step),'STORY_NEXT':str(step+10 if step<60 else 0),'SEQUENCE':'true'}


class StorySequenceAdapter(StoryNavigationAdapter):
    _binding=staticmethod(sequence_binding)
    _observation=staticmethod(sequence_observation)

    def finish(self,request_id,token):
        def settled(result):
            # A late Stop cannot undo a click that reached the story handler.
            if ((result['success'] is True or 'click' in result['events'])
                    and result['outcome'] not in ('advanced','finished')):
                raise ValueError('Story transition not yet established; retain ownership')
        result=self.observe(request_id,token)
        if not result['completed'] or not result['quiescent']:
            raise ValueError('Exact action is not quiescent')
        settled(result)
        if not result['closed']:
            result=self._exchange(request_id,token,'close')
        if not result['closed'] or not result['quiescent']:
            raise ValueError('Action closure unconfirmed')
        settled(result)
        with self.db:
            self.store._write_lock()
            self._owner(request_id,token)
            state=self.store.release(request_id,token)
        return {**result,'reservation_state':state}
