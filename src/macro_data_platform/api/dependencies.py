from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from macro_data_platform.database import get_session

SessionDependency = Annotated[Session, Depends(get_session)]
