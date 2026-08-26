"""Small domain objects used to describe ResolveX records.

Database queries remain in DatabaseManager and business rules remain in
services. These classes provide a clear, typed vocabulary for the domain.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class User:
	id: int
	name: str
	email: str
	role: str


@dataclass(frozen=True)
class Category:
	id: int
	name: str
	description: Optional[str] = None


@dataclass(frozen=True)
class Subcategory:
	id: int
	category_id: int
	name: str
	description: Optional[str] = None


@dataclass(frozen=True)
class Location:
	id: int
	building: str
	floor: Optional[str] = None
	room: Optional[str] = None
	facility_type: Optional[str] = None
	specific_area: Optional[str] = None


@dataclass(frozen=True)
class Department:
	id: int
	name: str
	description: Optional[str] = None


@dataclass(frozen=True)
class IssueHistory:
	id: int
	issue_id: int
	action: str
	user_id: Optional[int] = None
	note: Optional[str] = None
	timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class Issue:
	id: int
	title: str
	description: str
	category_id: int
	location_id: int
	priority: str
	status: str
	reporter_id: int
	subcategory_id: Optional[int] = None
	department_id: Optional[int] = None
	assigned_to: Optional[int] = None
	created_at: Optional[datetime] = None
	updated_at: Optional[datetime] = None
	due_at: Optional[datetime] = None
	resolved_at: Optional[datetime] = None
	closed_at: Optional[datetime] = None
